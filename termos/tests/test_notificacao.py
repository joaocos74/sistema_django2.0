import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, Client
from django.urls import reverse
from register.models import Estabelecimento, Vigilancia
from ..models import AutoTermoPadrao, NotificacaoPadrao, NotificacaoEmitida, SequenciaNotificacao
from ..services import gerar_notificacao


class NotificacaoTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('fiscal')
        self.est = Estabelecimento.objects.create(nome_fantasia='Mercado', email='empresa@example.com')
        Vigilancia.objects.create(estabelecimento=self.est, fiscal=self.user)
        self.client.force_login(self.user)
        self.url = reverse('termos:notificacao', args=[self.est.pk])
        relogio = patch('termos.services.timezone.localdate', return_value=date(2026, 10, 13))
        relogio.start()
        self.addCleanup(relogio.stop)

    def dados(self, **kwargs):
        response = self.client.get(self.url)
        return {'emissao_token': response.context['emissao_token'], 'campo_33': 'Texto', **kwargs}

    def test_abrir_nao_reserva(self):
        for _ in range(2):
            response = self.client.get(self.url)
            self.assertEqual(response.context['numero_notificacao'], '01/2026')
            self.assertContains(response, '>Gerar</button>')
            self.assertNotContains(response, 'data-padrao="numero_notificacao"')
        self.assertFalse(SequenciaNotificacao.objects.exists())
        self.assertFalse(NotificacaoEmitida.objects.exists())

    def test_sequencia_global_e_repeticao(self):
        dados = self.dados(numero_notificacao='999/2000')
        outro = Estabelecimento.objects.create(nome_fantasia='Outro')
        fiscal = get_user_model().objects.create_user('outro')
        Vigilancia.objects.create(estabelecimento=outro, fiscal=fiscal)
        client = Client()
        client.force_login(fiscal)
        url = reverse('termos:notificacao', args=[outro.pk])
        previa = client.get(url)
        response = self.client.post(self.url, dados)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['url'], self.client.post(self.url, dados).json()['url'])
        self.assertEqual(client.post(url, {'emissao_token': previa.context['emissao_token']}).status_code, 200)
        self.assertEqual(list(NotificacaoEmitida.objects.order_by('numero').values_list('numero', flat=True)), [1, 2])
        self.assertEqual(self.client.get(self.url).context['numero_notificacao'], '03/2026')

    def test_virada_do_ano(self):
        self.client.post(self.url, self.dados())
        with patch('termos.services.timezone.localdate', return_value=date(2027, 1, 1)):
            self.assertEqual(self.client.get(self.url).context['numero_notificacao'], '01/2027')
            self.client.post(self.url, self.dados())
        self.assertEqual(set(NotificacaoEmitida.objects.values_list('ano', 'numero')), {(2026, 1), (2027, 1)})

    def test_snapshot_e_historico(self):
        AutoTermoPadrao.objects.create(estabelecimento=self.est, campos={'campo_33': 'Auto original'}, atualizado_por=self.user)
        response = self.client.post(self.url, self.dados(campo_04='Nome salvo', autoridades_extras='[{"nome":"Fiscal","matricula":"123","funcao":"Autoridade"}]'))
        self.est.nome_fantasia = 'Alterado'
        self.est.save()
        documento = self.client.get(response.json()['url'])
        self.assertEqual(documento.context['padrao_salvo']['campo_04'], 'Nome salvo')
        self.assertContains(documento, 'data-emitida="true"')
        self.assertNotContains(documento, 'id="salvar-padrao"')
        self.assertEqual(self.client.post(response.json()['url'], {}).status_code, 405)
        self.assertEqual(AutoTermoPadrao.objects.get().campos['campo_33'], 'Auto original')
        self.assertEqual(NotificacaoPadrao.objects.get().campos, NotificacaoEmitida.objects.get().campos)
        self.assertContains(self.client.get(reverse('termos:historico', args=[self.est.pk])), '01/2026')

    def test_validacao_permissoes_e_csrf(self):
        dados = self.dados(campo_33='x' * 10001)
        self.assertEqual(self.client.post(self.url, dados).status_code, 400)
        self.assertEqual(self.client.post(self.url, {}).status_code, 400)
        outro = get_user_model().objects.create_user('outro')
        self.client.force_login(outro)
        self.assertEqual(self.client.post(self.url, dados).status_code, 403)
        outro.is_superuser = True
        outro.save()
        dados['campo_33'] = 'Texto'
        self.assertEqual(self.client.post(self.url, dados).status_code, 400)
        self.assertFalse(NotificacaoEmitida.objects.exists())
        self.assertFalse(SequenciaNotificacao.objects.exists())
        seguro = Client(enforce_csrf_checks=True)
        seguro.force_login(outro)
        self.assertEqual(seguro.post(self.url, self.dados()).status_code, 403)
        self.assertEqual(self.client.post(self.url, self.dados()).status_code, 200)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_falha_reverte_numero(self):
        with patch('termos.services.NotificacaoPadrao.objects.update_or_create', side_effect=ValueError('falha')):
            with self.assertRaises(ValueError):
                gerar_notificacao(self.est, self.user, {}, uuid.uuid4())
        self.assertFalse(NotificacaoEmitida.objects.exists())
        self.assertFalse(SequenciaNotificacao.objects.exists())


class ConcorrenciaTests(TransactionTestCase):
    def test_emissoes_simultaneas(self):
        user = get_user_model().objects.create_user('fiscal')
        est = Estabelecimento.objects.create(nome_fantasia='Mercado')
        def emitir(_):
            close_old_connections()
            try:
                return gerar_notificacao(est, user, {}, uuid.uuid4()).numero
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            numeros = list(pool.map(emitir, range(2)))
        self.assertEqual(sorted(numeros), [1, 2])
