from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from denuncias.models import Denuncia
from register.models import Estabelecimento, Vigilancia


class MinhasPendenciasTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('fiscal')
        self.outro = get_user_model().objects.create_user('outro')
        self.est = Estabelecimento.objects.create(nome_fantasia='Mercado', cnpj='123', razao_social='Mercado')
        self.client.force_login(self.user)
        relogio = patch('home.views.timezone.localdate', return_value=date(2026, 10, 13))
        relogio.start()
        self.addCleanup(relogio.stop)

    def inspecao(self, **kwargs):
        dados = dict(estabelecimento=self.est, fiscal=self.user, ano_previsto=2026,
                     mes_previsto=10, inspecao_status='a_fazer')
        dados.update(kwargs)
        return Vigilancia.objects.create(**dados)

    def denuncia(self, **kwargs):
        dados = dict(criado_por=self.outro, fiscal_responsavel=self.user, razao_social='Empresa',
                     cnpj='123', status='pendente', data_denuncia=date(2025, 1, 1))
        dados.update(kwargs)
        return Denuncia.objects.create(**dados)

    def test_inspecoes_somente_do_usuario_mes_ano_e_a_fazer(self):
        esperado = self.inspecao()
        self.inspecao(fiscal=self.outro)
        self.inspecao(mes_previsto=9)
        self.inspecao(ano_previsto=2025)
        self.inspecao(inspecao_status='concluido')
        self.inspecao(inspecao_status='pendente')
        self.inspecao(mes_previsto=None)
        response = self.client.get(reverse('home:index'))
        self.assertEqual(list(response.context['inspecoes_pendentes']), [esperado])
        self.assertContains(response, reverse('register_view:analisar', args=[self.est.pk]))

    def test_denuncias_abertas_de_qualquer_mes_do_responsavel(self):
        pendente = self.denuncia()
        andamento = self.denuncia(status='em_andamento', data_denuncia=None)
        self.denuncia(status='concluido')
        self.denuncia(fiscal_responsavel=self.outro, criado_por=self.user)
        self.denuncia(fiscal_responsavel=None, criado_por=self.user)
        response = self.client.get(reverse('home:index'))
        self.assertEqual(list(response.context['denuncias_pendentes']), [pendente, andamento])
        self.assertContains(response, f'?editar={pendente.pk}')

    def test_paginacao_independente_limita_volume(self):
        for _ in range(7):
            self.inspecao()
            self.denuncia()
        response = self.client.get(reverse('home:index'), {'insp_page': 2})
        self.assertEqual(len(response.context['inspecoes_pendentes']), 2)
        self.assertEqual(len(response.context['denuncias_pendentes']), 5)
        self.assertEqual(response.context['inspecoes_pendentes'].paginator.count, 7)
        self.assertContains(response, 'insp_page=2&amp;den_page=2#pendencias')

    def test_estabelecimento_inativo_nao_gera_pendencia(self):
        self.inspecao()
        self.est.status = True
        self.est.save()
        response = self.client.get(reverse('home:index'))
        self.assertEqual(response.context['inspecoes_pendentes'].paginator.count, 0)

    def test_admin_tambem_ve_somente_suas_pendencias(self):
        self.user.is_superuser = True
        self.user.save()
        self.inspecao(fiscal=self.outro)
        self.denuncia(fiscal_responsavel=self.outro)
        response = self.client.get(reverse('home:index'))
        self.assertContains(response, 'Nenhuma inspeção a fazer neste mês.')
        self.assertContains(response, 'Nenhuma denúncia pendente para você.')

    def test_home_exige_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('home:index')).status_code, 302)
