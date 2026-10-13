from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Arquivo


class ArquivosTests(TestCase):
    def setUp(self):
        pasta = TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        storage = patch.object(Arquivo._meta.get_field('arquivo'), 'storage', FileSystemStorage(location=pasta.name))
        storage.start()
        self.addCleanup(storage.stop)
        self.user = get_user_model().objects.create_user('fiscal')
        self.client.force_login(self.user)

    def enviar(self, nome='Planilha', filename='controle.xlsx', conteudo=b'conteudo'):
        return self.client.post(reverse('arquivos:index'), {
            'nome': nome, 'descricao': 'Arquivo geral',
            'arquivo': SimpleUploadedFile(filename, conteudo),
        })

    def test_envio_historico_e_download(self):
        self.assertRedirects(self.enviar(), reverse('arquivos:index'))
        registro = Arquivo.objects.get()
        self.assertEqual(registro.enviado_por, self.user)
        self.assertEqual(registro.nome_original, 'controle.xlsx')
        self.assertEqual(registro.tamanho, 8)
        self.assertNotEqual(registro.arquivo.name, registro.nome_original)
        response = self.client.get(reverse('arquivos:index'))
        self.assertContains(response, 'controle.xlsx')
        self.assertContains(response, 'fiscal')
        response = self.client.get(reverse('arquivos:baixar', args=[registro.pk]))
        self.assertEqual(b''.join(response.streaming_content), b'conteudo')
        self.assertIn('attachment;', response['Content-Disposition'])
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        # O fechamento manual dispara request_finished fora do wrapper do test client.
        # Preserve a transação de TestCase; feche normalmente o arquivo da resposta.
        with patch('django.db.backends.base.base.BaseDatabaseWrapper.close_if_unusable_or_obsolete'):
            response.close()

    def test_login_obrigatorio(self):
        self.enviar()
        self.client.logout()
        self.assertEqual(self.client.get(reverse('arquivos:index')).status_code, 302)
        self.assertEqual(self.enviar().status_code, 302)
        self.assertEqual(self.client.get(reverse('arquivos:baixar', args=[Arquivo.objects.get().pk])).status_code, 302)
        self.assertEqual(Arquivo.objects.count(), 1)

    def test_campos_obrigatorios_e_tamanho(self):
        response = self.client.post(reverse('arquivos:index'), {'nome': ''})
        self.assertIn('nome', response.context['form'].errors)
        self.assertIn('arquivo', response.context['form'].errors)
        with override_settings(ARQUIVOS_MAX_BYTES=2):
            response = self.enviar()
            self.assertIn('arquivo', response.context['form'].errors)
        self.assertFalse(Arquivo.objects.exists())

    def test_nomes_iguais_nao_sobrescrevem_e_busca(self):
        self.enviar(nome='Primeiro', conteudo=b'primeiro')
        self.enviar(nome='Segundo', conteudo=b'segundo')
        registros = list(Arquivo.objects.all())
        self.assertEqual(len(registros), 2)
        self.assertNotEqual(registros[0].arquivo.name, registros[1].arquivo.name)
        response = self.client.get(reverse('arquivos:index'), {'q': 'Segundo'})
        self.assertEqual(response.context['pagina'].paginator.count, 1)
        self.assertEqual(response.context['pagina'][0].nome, 'Segundo')

    def test_arquivo_ausente_retorna_404(self):
        self.enviar()
        registro = Arquivo.objects.get()
        registro.arquivo.delete(save=False)
        self.assertEqual(self.client.get(reverse('arquivos:baixar', args=[registro.pk])).status_code, 404)

    def test_autor_nao_pode_ser_forjado(self):
        outro = get_user_model().objects.create_user('outro')
        self.client.post(reverse('arquivos:index'), {
            'nome': 'Arquivo', 'enviado_por': outro.pk,
            'arquivo': SimpleUploadedFile('nota.txt', b'nota'),
        })
        self.assertEqual(Arquivo.objects.get().enviado_por, self.user)
