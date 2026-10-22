from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from register.forms import InspecaoForm
from register.models import Estabelecimento, Tipo, Vigilancia


class NaoConformidadesTests(TestCase):
    def setUp(self):
        self.fiscal = get_user_model().objects.create_user('fiscal')
        self.outro = get_user_model().objects.create_user('outro')
        self.est = Estabelecimento.objects.create(
            nome_fantasia='Mercado teste', razao_social='Mercado teste', cnpj='123',
            logradouro='Rua teste', numero='1', bairro='Centro', cidade='Taiobeiras',
            uf='MG', cep='39550-000', phone='(38) 99999-9999',
        )
        Tipo.objects.create(estabelecimento=self.est, risco='I', cnae_principal='4712-1/00', classe='Mercado')
        self.vig = Vigilancia.objects.create(estabelecimento=self.est, fiscal=self.fiscal,
                                            ano_previsto=2026, mes_previsto=10)
        self.url = reverse('register_view:analisar', args=[self.est.pk])
        self.client.force_login(self.fiscal)
        relogio = patch('django.utils.timezone.localdate', return_value=date(2026, 10, 22))
        relogio.start()
        self.addCleanup(relogio.stop)

    def payload(self, **changes):
        response = self.client.get(self.url)
        data = {}
        for form_name in ('form', 'inspecao_form'):
            for field in response.context[form_name]:
                value = field.value()
                data[field.html_name] = '' if value is None else value.isoformat() if hasattr(value, 'isoformat') else str(value)
        data.update(changes)
        return data

    def salvar(self, **changes):
        response = self.client.post(self.url, self.payload(**changes))
        self.assertEqual(response.status_code, 302, response.content.decode()[-4000:])
        return response

    def test_conclui_agendamento_preserva_historico_e_corrige_mesma_inspecao(self):
        self.salvar(data_realizacao='2026-09-01', nc_total='10', nc_criticas='2', nc_maiores='5')
        self.vig.refresh_from_db()
        self.assertEqual((self.vig.nc_total, self.vig.nc_criticas, self.vig.nc_maiores), (10, 2, 5))
        self.assertEqual(self.est.fiscalizacoes.count(), 1)
        self.salvar(data_realizacao='2026-10-01', nc_total='6', nc_criticas='1', nc_maiores='3')
        self.assertEqual(self.est.fiscalizacoes.count(), 2)
        self.vig.refresh_from_db()
        self.assertEqual(self.vig.nc_total, 10)
        self.salvar(nc_total='7', nc_criticas='2', nc_maiores='3')
        self.assertEqual(self.est.fiscalizacoes.count(), 2)
        response = self.client.get(self.url)
        self.assertEqual([(r['data'], r['total'], r['criticas'], r['maiores'])
                          for r in response.context['nao_conformidades']],
                         [('01/09/2026', 10, 2, 5), ('01/10/2026', 7, 2, 3)])

    def test_valida_quantidades_inteiras_nao_negativas_e_subconjuntos(self):
        base = {'inspecao_status': 'a_fazer', 'data_realizacao': '2026-10-01',
                'plano_aplicado': 'nao_requerido', 'termo_ciencia': 'nao_requerido',
                'interdicao': 'nao_requerido', 'processo': 'nao_requerido',
                'nc_total': '10', 'nc_criticas': '2', 'nc_maiores': '3'}
        for changes, field in [
            ({'nc_total': '4'}, 'nc_total'),
            ({'nc_criticas': '-1'}, 'nc_criticas'),
            ({'nc_maiores': '1.5'}, 'nc_maiores'),
            ({'nc_total': '2147483648'}, 'nc_total'),
            ({'nc_maiores': ''}, 'nc_maiores'),
            ({'data_realizacao': ''}, 'data_realizacao'),
        ]:
            with self.subTest(changes=changes):
                form = InspecaoForm(data=base | changes)
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)
        self.assertTrue(InspecaoForm(data=base).is_valid())

    def test_invalido_nao_modifica_cadastro_nem_inspecao(self):
        response = self.client.post(self.url, self.payload(
            nome_fantasia='Alteração indevida', data_realizacao='2026-10-01',
            nc_total='2', nc_criticas='2', nc_maiores='3'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'não pode ultrapassar o total')
        self.est.refresh_from_db()
        self.vig.refresh_from_db()
        self.assertEqual(self.est.nome_fantasia, 'Mercado teste')
        self.assertIsNone(self.vig.nc_total)
        self.assertIsNone(self.vig.data_realizacao)

    def test_nao_informado_e_diferente_de_zero(self):
        self.salvar(data_realizacao='2026-10-01')
        self.assertEqual(self.client.get(self.url).context['nao_conformidades'], [])
        self.vig.refresh_from_db()
        self.assertIsNone(self.vig.nc_total)
        self.salvar(nc_total='0', nc_criticas='0', nc_maiores='0')
        rows = self.client.get(self.url).context['nao_conformidades']
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['total'], rows[0]['criticas'], rows[0]['maiores']), (0, 0, 0))
        self.salvar(nc_total='', nc_criticas='', nc_maiores='')
        self.assertEqual(self.client.get(self.url).context['nao_conformidades'], [])

    def test_formulario_antigo_sem_campos_preserva_contagem(self):
        self.salvar(data_realizacao='2026-10-01', nc_total='10', nc_criticas='2', nc_maiores='3')
        payload = self.payload()
        for campo in Vigilancia.campos_nao_conformidades:
            del payload[campo]
        self.assertEqual(self.client.post(self.url, payload).status_code, 302)
        self.vig.refresh_from_db()
        self.assertEqual((self.vig.nc_total, self.vig.nc_criticas, self.vig.nc_maiores), (10, 2, 3))

    def test_grafico_ordena_por_data_e_isola_estabelecimento(self):
        for day in (20, 5):
            Vigilancia.objects.create(estabelecimento=self.est, fiscal=self.fiscal,
                data_realizacao=date(2026, 10, day), nc_total=5, nc_criticas=2, nc_maiores=3)
        other = Estabelecimento.objects.create(nome_fantasia='Outro')
        Vigilancia.objects.create(estabelecimento=other, fiscal=self.fiscal,
            data_realizacao=date(2026, 10, 1), nc_total=999, nc_criticas=999, nc_maiores=0)
        rows = self.client.get(self.url).context['nao_conformidades']
        self.assertEqual([r['data'] for r in rows], ['05/10/2026', '20/10/2026'])
        self.assertNotIn(999, [r['total'] for r in rows])

    def test_outro_fiscal_somente_leitura_admin_pode_editar(self):
        payload = self.payload(data_realizacao='2026-10-01', nc_total=3, nc_criticas=1, nc_maiores=2)
        self.client.force_login(self.outro)
        self.assertFalse(self.client.get(self.url).context['pode_editar'])
        self.assertEqual(self.client.post(self.url, payload).status_code, 302)
        self.vig.refresh_from_db()
        self.assertIsNone(self.vig.nc_total)
        self.outro.is_superuser = True
        self.outro.save()
        self.assertEqual(self.client.post(self.url, payload).status_code, 302)
        self.vig.refresh_from_db()
        self.assertEqual(self.vig.nc_total, 3)

    def test_banco_bloqueia_contagens_inconsistentes(self):
        for changes in [
            {'nc_total': 5},
            {'nc_total': 2, 'nc_criticas': 2, 'nc_maiores': 2, 'data_realizacao': date(2026, 10, 1)},
            {'nc_total': 2, 'nc_criticas': -1, 'nc_maiores': 2, 'data_realizacao': date(2026, 10, 1)},
            {'nc_total': 0, 'nc_criticas': 0, 'nc_maiores': 0},
        ]:
            with self.subTest(changes=changes), self.assertRaises(IntegrityError), transaction.atomic():
                Vigilancia.objects.filter(pk=self.vig.pk).update(**changes)
