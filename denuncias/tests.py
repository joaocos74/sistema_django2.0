from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from register.models import Estabelecimento
from .models import Denuncia


class DenunciasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.autor = get_user_model().objects.create_user('autor')
        cls.outro = get_user_model().objects.create_user('outro')
        cls.est = Estabelecimento.objects.create(cnpj='61.480.081/0001-69', nome_fantasia='Local Teste', razao_social='Empresa Teste')
        cls.est2 = Estabelecimento.objects.create(cnpj='12345678901', nome_fantasia='Outro Local', razao_social='Outra Empresa')

    def setUp(self):
        self.client.force_login(self.autor)
        self.dados = {'cnpj': '61480081000169', 'razao_social': 'Empresa Teste',
                      'motivo': 'Motivo exclusivo do primeiro cadastro', 'status': 'pendente',
                      'data_denuncia': '2026-10-12'}

    def criar(self):
        response = self.client.post(reverse('denuncias:index'), self.dados)
        self.assertEqual(response.status_code, 302)
        return Denuncia.objects.get()

    def test_vincula_documento_sem_pontuacao_e_filtra_historico(self):
        denuncia = self.criar()
        self.assertEqual(denuncia.estabelecimento, self.est)
        self.assertEqual(denuncia.criado_por, self.autor)
        response = self.client.get(reverse('register_view:analisar', args=[self.est.pk]))
        self.assertContains(response, self.dados['motivo'])
        self.assertContains(response, 'historico-denuncias')
        response = self.client.get(reverse('register_view:analisar', args=[self.est2.pk]))
        self.assertNotContains(response, self.dados['motivo'])

    def test_registro_sem_cadastro_nao_cria_estabelecimento(self):
        self.dados['cnpj'] = '99999999999'
        denuncia = self.criar()
        self.assertIsNone(denuncia.estabelecimento)
        self.assertEqual(Estabelecimento.objects.count(), 2)
        self.assertEqual(self.client.get(reverse('denuncias:index')).status_code, 200)

    def test_rejeita_vinculo_forjado_e_documento_ambiguo(self):
        self.dados['cadastro_id'] = self.est2.pk
        self.assertEqual(self.client.post(reverse('denuncias:index'), self.dados).status_code, 200)
        self.assertFalse(Denuncia.objects.exists())
        self.dados.pop('cadastro_id')
        Estabelecimento.objects.create(cnpj='61480081000169', razao_social='Duplicado')
        self.assertEqual(self.client.post(reverse('denuncias:index'), self.dados).status_code, 200)
        self.assertFalse(Denuncia.objects.exists())

    def test_outro_usuario_nao_edita(self):
        denuncia = self.criar()
        self.client.force_login(self.outro)
        self.dados.update(denuncia_id=denuncia.pk, motivo='Alterado sem permissao')
        self.assertEqual(self.client.post(reverse('denuncias:index'), self.dados).status_code, 403)
        denuncia.refresh_from_db()
        self.assertNotEqual(denuncia.motivo, self.dados['motivo'])

    def test_fiscal_designado_edita_e_historico_atualiza(self):
        self.dados['fiscal_responsavel'] = self.outro.pk
        denuncia = self.criar()
        self.client.force_login(self.outro)
        self.dados.update(denuncia_id=denuncia.pk, status='concluido', medidas_adotadas='Medida confirmada')
        self.assertEqual(self.client.post(reverse('denuncias:index'), self.dados).status_code, 302)
        denuncia.refresh_from_db()
        self.assertEqual(denuncia.status, 'concluido')
        self.assertEqual(denuncia.criado_por, self.autor)
        self.assertContains(self.client.get(reverse('register_view:analisar', args=[self.est.pk])), 'Medida confirmada')

    def test_datas_e_status_invalidos_preservam_formulario(self):
        for valores in ({'data_denuncia': '2026-02-31'}, {'status': 'invalido'}, {'data_tratativa': '2026-10-01'}):
            response = self.client.post(reverse('denuncias:index'), self.dados | valores)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, self.dados['motivo'])
            self.assertFalse(Denuncia.objects.exists())

    def test_busca_e_preenchimento_pelo_cadastro(self):
        response = self.client.get(reverse('denuncias:buscar_cnpj'), {'cnpj': '61480081000169'})
        self.assertEqual(response.json()['dados']['id'], self.est.pk)
        self.assertContains(self.client.get(reverse('denuncias:index'), {'estabelecimento': self.est.pk}), 'Local Teste')

    def test_login_csrf_e_escape(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('denuncias:index')).status_code, 302)
        protegido = Client(enforce_csrf_checks=True)
        protegido.force_login(self.autor)
        self.assertEqual(protegido.post(reverse('denuncias:index'), self.dados).status_code, 403)
        self.client.force_login(self.autor)
        self.dados['razao_social'] = '<script>alert(1)</script>'
        self.dados['cnpj'] = '99999999999'
        self.criar()
        response = self.client.get(reverse('denuncias:index'))
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_edicao_preserva_vinculo_apos_mudanca_cadastro(self):
        denuncia = self.criar()
        self.est.cnpj = '98765432100'
        self.est.save()
        self.dados.update(denuncia_id=denuncia.pk, cadastro_id=self.est.pk, status='em_andamento')
        self.assertEqual(self.client.post(reverse('denuncias:index'), self.dados).status_code, 302)
        denuncia.refresh_from_db()
        self.assertEqual(denuncia.estabelecimento, self.est)

    def test_dados_cadastrados_bloqueados_no_servidor(self):
        self.dados.update(razao_social='Forjado', nome_fantasia='Forjado', endereco='Forjado')
        denuncia = self.criar()
        self.assertEqual(denuncia.razao_social, self.est.razao_social)
        self.assertEqual(denuncia.nome_fantasia, self.est.nome_fantasia)
        self.assertNotEqual(denuncia.endereco, 'Forjado')
        response = self.client.get(reverse('denuncias:index'), {'editar': denuncia.pk})
        for campo in ('cnpj', 'razao_social', 'nome_fantasia', 'endereco'):
            self.assertTrue(response.context['form'].fields[campo].disabled)
        self.dados.update(denuncia_id=denuncia.pk, cnpj='99999999999', motivo='Novo motivo')
        self.assertEqual(self.client.post(reverse('denuncias:index'), self.dados).status_code, 302)
        denuncia.refresh_from_db()
        self.assertEqual(denuncia.cnpj, self.est.cnpj)
        self.assertEqual(denuncia.razao_social, self.est.razao_social)
        self.assertEqual(denuncia.motivo, 'Novo motivo')
