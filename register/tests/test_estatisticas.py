from django.test import TestCase

from datetime import date
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from denuncias.models import Denuncia
from redesim.models import RegistroRedesim
from ..models import Estabelecimento
from ..estatisticas_modulos import metricas_modulos, anos_modulos


class EstatisticasModulosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.fiscal = get_user_model().objects.create_user('responsavel')
        cls.autor = get_user_model().objects.create_user('autor')
        cls.est = Estabelecimento.objects.create(cnpj='12345678901', nome_fantasia='Local', razao_social='Empresa')
        for status, tipo, mes in [('pendente', 'Produto', 1), ('em_andamento', 'Serviço', 2), ('concluido', 'Produto', 2)]:
            Denuncia.objects.create(criado_por=cls.autor, fiscal_responsavel=cls.fiscal,
                cnpj='12345678901', razao_social='Empresa', status=status, tipo=tipo,
                data_denuncia=date(2025, mes, 10))
        Denuncia.objects.create(criado_por=cls.autor, cnpj='99999999999', razao_social='Sem cadastro', data_denuncia=date(2024, 1, 1))
        for mes, classe, nivel in [(1, 'COMERCIO', 'NIVEL 1'), (2, 'SERVICOS', 'NIVEL 2'), (2, 'SERVICOS', 'NIVEL 2')]:
            RegistroRedesim.objects.create(estabelecimento=cls.est, fiscal=cls.autor,
                data_liberacao=date(2025, mes, 10), classe=classe, nivel=nivel)
        RegistroRedesim.objects.create(estabelecimento=cls.est, fiscal=cls.fiscal)

    def cards(self, fiscal='todos'):
        return {card['id']: card for card in metricas_modulos(2025, fiscal)}

    def test_denuncias_status_tipos_fiscal_e_meses(self):
        cards = self.cards()
        total = cards['denuncias']['itens'][0]
        self.assertEqual([total[k] for k in ('total', 'pendente', 'em_andamento', 'concluido', 'produtos', 'servicos')], [3, 1, 1, 1, 2, 1])

    def test_redesim_conta_cada_liberacao(self):
        cards = self.cards()
        total = cards['redesim']['itens'][0]
        self.assertEqual(cards['redesim']['headers'], ['Período', 'Liberados'])
        self.assertEqual(total['liberacoes'], 3)

    def test_filtro_fiscal_usa_papel_de_cada_modulo(self):
        cards = self.cards(str(self.fiscal.pk))
        self.assertEqual(cards['denuncias']['itens'][0]['total'], 3)
        self.assertEqual(cards['redesim']['itens'][0]['liberacoes'], 0)
        cards = self.cards(str(self.autor.pk))
        self.assertEqual(cards['denuncias']['itens'][0]['total'], 0)
        self.assertEqual(cards['redesim']['itens'][0]['liberacoes'], 3)

    def test_anos_e_denuncia_sem_data(self):
        Denuncia.objects.create(criado_por=self.autor, cnpj='99999999999', razao_social='Sem data')
        self.assertTrue({2024, 2025, timezone.localdate().year}.issubset(anos_modulos()))
        cards = {c['id']: c for c in metricas_modulos(timezone.localdate().year, 'todos')}
        self.assertGreaterEqual(cards['denuncias']['itens'][0]['total'], 1)

    def test_renderiza_novas_tabelas_e_dados_dos_graficos(self):
        self.client.force_login(self.autor)
        response = self.client.get(reverse('register_view:estatisticas'), {'ano': '2025'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'js-metricas-modulos')
        self.assertContains(response, 'chart-redesim')
        self.assertContains(response, 'chart-denuncias')
        self.assertContains(response, 'id="denuncias"', count=1)
        self.assertContains(response, 'id="redesim"', count=1)
        self.assertNotContains(response, 'id="denuncias-mes"')
        self.assertNotContains(response, 'id="redesim-classe"')

    def test_filtros_combinados_e_independentes(self):
        filtros = {'denuncias_ano': '2025', 'denuncias_mes': '2',
                   'denuncias_tipo': 'Serviço', 'denuncias_status': 'em_andamento',
                   'denuncias_fiscal': str(self.fiscal.pk), 'redesim_ano': '2025',
                   'redesim_mes': '2', 'redesim_classe': 'SERVICOS',
                   'redesim_risco': 'NIVEL 2', 'redesim_fiscal': str(self.autor.pk)}
        cards = {c['id']: c for c in metricas_modulos(2025, 'todos', filtros)}
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards['denuncias']['itens'][0]['total'], 1)
        self.assertEqual(cards['denuncias']['itens'][0]['servicos'], 1)
        self.assertEqual(cards['redesim']['itens'][0]['liberacoes'], 2)
        filtros['denuncias_status'] = 'concluido'
        cards = {c['id']: c for c in metricas_modulos(2025, 'todos', filtros)}
        self.assertEqual(cards['denuncias']['itens'][0]['total'], 0)
        self.assertEqual(cards['redesim']['itens'][0]['liberacoes'], 2)
        self.assertIn({'nome': 'redesim_classe', 'valor': 'SERVICOS'}, cards['denuncias']['preservados'])

    def test_ano_especifico_e_filtros_invalidos(self):
        cards = {c['id']: c for c in metricas_modulos(2025, 'todos', {'denuncias_ano': '2024', 'redesim_mes': '99'})}
        self.assertEqual(cards['denuncias']['itens'][0]['total'], 1)
        self.assertEqual(cards['redesim']['itens'][0]['liberacoes'], 3)
