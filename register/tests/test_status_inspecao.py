from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from register.models import Estabelecimento, Vigilancia


class SituacaoInspecaoTests(TestCase):
    def setUp(self):
        self.fiscal = get_user_model().objects.create_user('fiscal')
        self.outro = get_user_model().objects.create_user('outro')
        self.est = Estabelecimento.objects.create(nome_fantasia='Mercado de teste')
        self.client.force_login(self.fiscal)
        relogio = patch('django.utils.timezone.localdate', return_value=date(2026, 10, 22))
        relogio.start()
        self.addCleanup(relogio.stop)

    def inspecao(self, **kwargs):
        dados = dict(estabelecimento=self.est, fiscal=self.fiscal,
                     ano_previsto=2026, mes_previsto=10, inspecao_status='a_fazer')
        dados.update(kwargs)
        return Vigilancia.objects.create(**dados)

    def pesquisa(self, **params):
        return self.client.get(reverse('register_view:pesquisar'), params)

    def pendencias(self):
        return list(self.client.get(reverse('home:index')).context['inspecoes_pendentes'])

    def cronograma(self):
        response = self.client.get(reverse('register_view:cronograma'))
        return [item for grupo in ('q1', 'q2', 'q3', 'sem_agendamento') for item in response.context[grupo]]

    def test_inspecao_antiga_concluida_volta_a_fazer_no_ano_atual(self):
        vig = self.inspecao(inspecao_status='concluido', data_realizacao=date(2025, 10, 1))
        self.assertEqual(self.pendencias(), [vig])
        self.assertEqual(self.cronograma()[0]['status'], 'A FAZER')
        self.assertEqual(self.pesquisa(inspecao_status='a_fazer').context['estabelecimentos'], [self.est])
        self.assertEqual(self.pesquisa(inspecao_status='concluido').context['estabelecimentos'], [])

    def test_data_do_ano_atual_prevalece_sobre_status_gravado(self):
        self.inspecao(inspecao_status='pendente', data_realizacao=date(2026, 10, 1))
        self.assertEqual(self.pendencias(), [])
        self.assertEqual(self.cronograma()[0]['status'], 'REALIZADO')
        self.assertEqual(self.pesquisa(inspecao_status='concluido').context['estabelecimentos'], [self.est])
        self.assertEqual(self.pesquisa(inspecao_status='pendente').context['estabelecimentos'], [])

    def test_ultima_inspecao_impede_pendencias_e_filtros_do_historico(self):
        self.inspecao(inspecao_status='pendente', data_alvara=date(2025, 10, 1))
        self.inspecao(data_realizacao=date(2026, 10, 2), data_alvara=date(2026, 10, 3))
        self.assertEqual(self.pendencias(), [])
        self.assertEqual(self.pesquisa(inspecao_status='pendente').context['estabelecimentos'], [])
        self.assertEqual(self.pesquisa(alvara_mes='2025-10').context['estabelecimentos'], [])
        response = self.pesquisa(inspecao_status='concluido', alvara_mes='2026-10')
        self.assertEqual(response.context['estabelecimentos'], [self.est])

    def test_fiscal_atual_recebe_pendencia_sem_duplicar_historico(self):
        self.inspecao()
        atual = self.inspecao(fiscal=self.outro)
        self.assertEqual(self.pendencias(), [])
        self.client.force_login(self.outro)
        self.assertEqual(self.pendencias(), [atual])

    def test_pendente_e_sem_inspecao_concordam_entre_telas(self):
        self.assertEqual(self.cronograma()[0]['status'], 'A FAZER')
        self.assertEqual(self.pesquisa(inspecao_status='a_fazer').context['estabelecimentos'], [self.est])
        self.assertEqual(self.pendencias(), [])
        self.inspecao(inspecao_status='pendente')
        self.assertEqual(self.cronograma()[0]['status'], 'PENDENTE')
        self.assertEqual(self.pesquisa(inspecao_status='pendente').context['estabelecimentos'], [self.est])
        self.assertEqual(self.pendencias(), [])

    def test_periodo_pesquisado_define_ano_e_rejeita_periodo_invalido(self):
        self.inspecao(data_realizacao=date(2025, 10, 1))
        response = self.pesquisa(inspecao_status='concluido', inspecao_mes='2025-10')
        self.assertEqual(response.context['estabelecimentos'], [self.est])
        self.assertEqual(response.context['ano_inspecao'], 2025)
        self.assertEqual(self.pesquisa(inspecao_mes='invalido').context['estabelecimentos'], [])

    def test_reagendamento_usa_ano_do_cronograma_e_respeita_fiscal(self):
        vig = self.inspecao(ano_previsto=2025)
        self.assertEqual(self.cronograma()[0]['mes_previsto'], None)
        self.assertEqual(self.pendencias(), [])
        url = reverse('register_view:atualizar_mes_previsto')
        payload = {'estabelecimento_id': self.est.pk, 'mes_previsto': 10}
        self.client.force_login(self.outro)
        self.assertEqual(self.client.post(url, payload, content_type='application/json').status_code, 403)
        vig.refresh_from_db()
        self.assertEqual(vig.ano_previsto, 2025)
        self.client.force_login(self.fiscal)
        self.assertEqual(self.client.post(url, payload, content_type='application/json').status_code, 200)
        vig.refresh_from_db()
        self.assertEqual((vig.ano_previsto, vig.mes_previsto), (2026, 10))
        self.assertEqual(self.cronograma()[0]['mes_previsto'], 10)
        self.assertEqual(self.pendencias(), [vig])

    def test_rotulo_data_realizacao_acentuado(self):
        self.inspecao()
        self.assertContains(self.client.get(reverse('register_view:analisar', args=[self.est.pk])), 'Data de realização')
