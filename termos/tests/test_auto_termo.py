from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from register.models import Estabelecimento, Responsavel, RTResponsavel, Tipo, Vigilancia
from ..models import AutoTermoPadrao


class AutoTermoTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('fiscal', first_name='Maria', last_name='Silva')
        self.client.force_login(self.user)
        self.est = Estabelecimento.objects.create(nome_fantasia='Mercado Alfa', razao_social='Alfa Ltda',
            cnpj='12.345.678/0001-90', logradouro='Rua das Flores', numero='15', bairro='Centro',
            cidade='Taiobeiras', uf='MG', cep='39550-000', phone='3838450000', insc_municipal='1234')
        self.url = reverse('termos:auto_termo', args=[self.est.pk])

    def test_preenche_dados_e_relacionamentos_recentes(self):
        Responsavel.objects.create(estabelecimento=self.est, nome='Responsável antigo', cpf='123')
        Responsavel.objects.create(estabelecimento=self.est, nome='João Responsável', cpf='456',
                                   logradouro='Rua B', numero='20', bairro='Centro', cidade='Taiobeiras', uf='MG')
        RTResponsavel.objects.create(estabelecimento=self.est, nome='Ana Técnica', rg_conselho='CRF 123')
        Tipo.objects.create(estabelecimento=self.est, classe='ANTIGA', cnae_principal='1')
        Tipo.objects.create(estabelecimento=self.est, classe='MERCADO', cnae_principal='4712100')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for texto in ['Mercado Alfa', 'Alfa Ltda', '12.345.678/0001-90', 'Rua das Flores, 15, Centro',
                      'João Responsável', 'Ana Técnica', 'CRF 123', 'MERCADO / 4712100', 'Maria Silva']:
            self.assertContains(response, texto)
        self.assertNotContains(response, 'Responsável antigo')
        self.assertEqual(response.context['campo_03'], self.est.numero_pasta)
        self.assertEqual(response.context['campo_01'], 'Montes Claros-MG')
        self.assertEqual(response.context['campo_02'], 'Taiobeiras-MG')
        self.assertContains(response, 'MERCADO ALFA')
        self.assertEqual(response.context['campo_04'], self.est.nome_fantasia)
        self.assertEqual(response.context['campo_23'], '')
        self.assertEqual(response.context['campo_30'], '')

    def test_sem_relacionamentos_renderiza_campos_vazios(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['campo_14'], '')
        self.assertEqual(response.context['campo_26'], '')
        self.assertNotContains(response, 'None')
        self.assertNotContains(response, 'url_for')

    def test_login_existencia_e_somente_leitura(self):
        self.assertEqual(self.client.post(self.url, {'campo_04': 'Alterado'}).status_code, 403)
        self.est.refresh_from_db()
        self.assertEqual(self.est.nome_fantasia, 'Mercado Alfa')
        self.assertEqual(self.client.get(reverse('termos:auto_termo', args=[99999])).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_escapa_conteudo_do_cadastro(self):
        self.est.nome_fantasia = '<script>alert(1)</script>'
        self.est.save()
        response = self.client.get(self.url)
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_salva_padrao_por_estabelecimento_sem_alterar_cadastro(self):
        Vigilancia.objects.create(estabelecimento=self.est, fiscal=self.user)
        response = self.client.post(self.url, {'campo_37': 'Texto personalizado', 'campo_33': '',
            'chk_auto': 'True', 'chk_termo': 'False', 'campo_04': 'Não alterar'})
        self.assertEqual(response.status_code, 200)
        salvo = self.client.get(self.url).context['padrao_salvo']
        self.assertEqual(salvo['campo_37'], 'Texto personalizado')
        self.assertEqual(salvo['campo_33'], '')
        self.assertTrue(salvo['chk_auto'])
        self.assertFalse(salvo['chk_termo'])
        self.assertEqual(salvo['campo_04'], 'Não alterar')
        self.est.refresh_from_db()
        self.assertEqual(self.est.nome_fantasia, 'Mercado Alfa')
        outro = Estabelecimento.objects.create(nome_fantasia='Outro')
        response = self.client.get(reverse('termos:auto_termo', args=[outro.pk]))
        self.assertEqual(response.context['padrao_salvo'], {})
        self.client.post(self.url, {'campo_37': 'Revisado'})
        self.assertEqual(AutoTermoPadrao.objects.count(), 1)
        self.assertEqual(AutoTermoPadrao.objects.get().campos['campo_37'], 'Revisado')

    def test_permissoes_e_limites_do_padrao(self):
        outro = get_user_model().objects.create_user('outro')
        Vigilancia.objects.create(estabelecimento=self.est, fiscal=self.user)
        Vigilancia.objects.create(estabelecimento=self.est, fiscal=outro)
        self.assertEqual(self.client.post(self.url, {'campo_37': 'Texto'}).status_code, 403)
        self.user.is_superuser = True
        self.user.save()
        self.assertEqual(self.client.post(self.url, {'campo_37': 'Texto'}).status_code, 200)
        self.assertEqual(self.client.post(self.url, {'campo_37': 'x' * 10001}).status_code, 400)
        self.assertEqual(AutoTermoPadrao.objects.get().campos['campo_37'], 'Texto')

    def test_salva_campos_data_e_autoridades_adicionais(self):
        import json
        self.user.is_superuser = True
        self.user.save()
        extras = [{'nome': 'Fiscal adicional', 'funcao': 'Fiscal sanitário'}]
        dados = {'campo_01': '', 'campo_38_dia': '15', 'campo_38_hora': '09:30',
                 'autoridade_nome': 'Fiscal titular', 'campo_38_funcao_1': 'Fiscal',
                 'autoridades_extras': json.dumps(extras)}
        self.assertEqual(self.client.post(self.url, dados).status_code, 200)
        salvo = self.client.get(self.url).context['padrao_salvo']
        self.assertEqual(salvo['campo_01'], '')
        self.assertEqual(salvo['campo_38_hora'], '09:30')
        self.assertEqual(salvo['autoridades_extras'], extras)
        self.assertEqual(self.client.post(self.url, {'autoridades_extras': '[123]'}).status_code, 400)
