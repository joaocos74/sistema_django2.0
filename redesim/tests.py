from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from register.models import Estabelecimento, Tipo, Vigilancia
from .models import RegistroRedesim


class RedesimTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.fiscal = get_user_model().objects.create_user('fiscal')
        cls.outro = get_user_model().objects.create_user('outro')
        cls.admin = get_user_model().objects.create_superuser('admin', password='test-password')
        cls.est = Estabelecimento.objects.create(cnpj='61.480.081/0001-69', nome_fantasia='Local', razao_social='Empresa')
        cls.tipo = Tipo.objects.create(estabelecimento=cls.est, risco='II', classe='COMERCIO', cnae_principal='1234')
        cls.vigilancia = Vigilancia.objects.create(estabelecimento=cls.est, fiscal=cls.fiscal)

    def setUp(self):
        clock = patch("django.utils.timezone.localdate", return_value=date(2026, 10, 13))
        clock.start()
        self.addCleanup(clock.stop)
        self.client.force_login(self.fiscal)
        self.dados = {'estabelecimento_id': self.est.pk, 'cnpj_ou_cpf': '61480081000169',
                      'alvara': '2026-10-12', 'observacoes': 'Observacao da liberacao'}

    def test_busca_classificacao_e_fiscal_atuais(self):
        Tipo.objects.create(estabelecimento=self.est, risco='III', classe='NOVA', cnae_principal='9999')
        response = self.client.get(reverse('redesim:buscar_cnpj'), {'documento': '61480081000169'})
        self.assertEqual(response.json()['dados']['nivel'], 'NIVEL 3')
        self.assertEqual(response.json()['dados']['fiscal_responsavel'], 'fiscal')

    def test_liberacao_snapshot_nao_altera_cadastro(self):
        self.dados['razao_social'] = 'Nome forjado'
        response = self.client.post(reverse('redesim:index'), self.dados)
        self.assertEqual(response.status_code, 302)
        registro = RegistroRedesim.objects.get()
        self.assertEqual(registro.razao_social, 'Empresa')
        self.assertEqual(registro.fiscal, self.fiscal)
        self.vigilancia.refresh_from_db()
        self.assertEqual(self.vigilancia.data_alvara, date(2026, 10, 12))
        self.assertEqual(self.vigilancia.obs, self.dados['observacoes'])
        self.est.razao_social = 'Nome posterior'
        self.est.save()
        self.assertEqual(self.client.get(reverse('redesim:listar')).json()[0]['razao_social'], 'Empresa')
        self.assertEqual(Vigilancia.objects.count(), 1)

    def test_nao_cria_cadastro_e_rejeita_id_trocado(self):
        for valores in ({'cnpj_ou_cpf': '99999999999'}, {'estabelecimento_id': self.est.pk + 100}):
            self.client.post(reverse('redesim:index'), self.dados | valores)
        self.assertFalse(RegistroRedesim.objects.exists())
        self.assertEqual(Estabelecimento.objects.count(), 1)

    def test_outro_usuario_libera_sem_trocar_fiscal(self):
        self.client.force_login(self.outro)
        self.assertEqual(self.client.post(reverse('redesim:index'), self.dados).status_code, 302)
        self.assertEqual(RegistroRedesim.objects.get().fiscal, self.outro)
        self.vigilancia.refresh_from_db()
        self.assertEqual(self.vigilancia.fiscal, self.fiscal)
        self.assertEqual(self.vigilancia.data_alvara, date(2026, 10, 12))
        self.assertEqual(self.vigilancia.obs, self.dados['observacoes'])

    def test_apenas_dois_campos_da_ultima_vigilancia_sao_atualizados(self):
        ultima = Vigilancia.objects.create(estabelecimento=self.est, fiscal=self.fiscal, obs='Anterior', mes_previsto=3)
        antes = Vigilancia.objects.filter(pk=ultima.pk).values().get()
        self.client.post(reverse('redesim:index'), self.dados | {'fiscal': self.outro.pk, 'mes_previsto': 8})
        depois = Vigilancia.objects.filter(pk=ultima.pk).values().get()
        self.assertEqual({k for k in antes if antes[k] != depois[k]}, {'data_alvara', 'obs'})
        self.vigilancia.refresh_from_db()
        self.assertIsNone(self.vigilancia.data_alvara)

    def test_historico_mais_recente_primeiro(self):
        self.client.post(reverse('redesim:index'), self.dados)
        self.client.post(reverse('redesim:index'), self.dados | {'alvara': '2026-10-01'})
        self.assertEqual([r['alvara'] for r in self.client.get(reverse('redesim:listar')).json()], ['01/10/2026', '12/10/2026'])

    def test_sem_vigilancia_nao_cria_registro_implicitamente(self):
        self.vigilancia.delete()
        self.client.post(reverse('redesim:index'), self.dados)
        self.assertFalse(Vigilancia.objects.exists())
        self.assertFalse(RegistroRedesim.objects.exists())

    def test_busca_inexistente_nao_altera_banco(self):
        response = self.client.get(reverse('redesim:buscar_cnpj'), {'documento': '99999999999'})
        self.assertFalse(response.json()['existe'])
        self.assertEqual(Estabelecimento.objects.count(), 1)
        self.assertEqual(Vigilancia.objects.count(), 1)
        self.assertFalse(RegistroRedesim.objects.exists())

    def test_validacao_data_e_csrf(self):
        self.client.post(reverse('redesim:index'), self.dados | {'alvara': '2026-02-31'})
        self.assertFalse(RegistroRedesim.objects.exists())
        protegido = Client(enforce_csrf_checks=True)
        protegido.force_login(self.fiscal)
        self.assertEqual(protegido.post(reverse('redesim:index'), self.dados).status_code, 403)

    def test_paginas_autenticadas(self):
        self.assertEqual(self.client.get(reverse('redesim:index')).status_code, 200)
        self.client.logout()
        for name in ('redesim:index', 'redesim:listar', 'redesim:buscar_cnpj'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 302)

    def test_data_futura_nao_altera_vigilancia_nem_historico(self):
        response = self.client.post(reverse('redesim:index'), self.dados | {'alvara': '2026-10-14'}, follow=True)
        self.assertContains(response, 'A data da liberação não pode ser futura.')
        self.assertFalse(RegistroRedesim.objects.exists())
        self.vigilancia.refresh_from_db()
        self.assertIsNone(self.vigilancia.data_alvara)
        self.assertEqual(self.vigilancia.obs, '')
        self.assertContains(response, 'max="2026-10-13"')

    def test_data_de_hoje_permitida_e_lista_autor_logado(self):
        self.outro.first_name = 'Maria'
        self.outro.last_name = 'Silva'
        self.outro.save()
        self.client.force_login(self.outro)
        self.client.post(reverse('redesim:index'), self.dados | {'alvara': '2026-10-13', 'fiscal': self.fiscal.pk})
        registro = RegistroRedesim.objects.get()
        self.assertEqual(registro.fiscal, self.outro)
        self.assertEqual(self.client.get(reverse('redesim:listar')).json()[0]['fiscal_liberacao'], 'Maria Silva')
        self.vigilancia.refresh_from_db()
        self.assertEqual(self.vigilancia.fiscal, self.fiscal)
