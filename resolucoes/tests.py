from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Resolucao, ClasseResolucao


PDF = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n'


class ResolucoesTests(TestCase):
    def setUp(self):
        pasta = TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        storage = patch.object(Resolucao._meta.get_field('arquivo'), 'storage', FileSystemStorage(location=pasta.name))
        storage.start()
        self.addCleanup(storage.stop)
        self.user = get_user_model().objects.create_user('fiscal')
        self.client.force_login(self.user)
        self.classe, _ = ClasseResolucao.objects.get_or_create(chave='alimentos', defaults={'nome': 'Alimentos'})

    def enviar(self, descricao='RDC 216 — Boas práticas', nome='resolucao.pdf', conteudo=PDF, **extra):
        return self.client.post(reverse('resolucoes:index'), {
            'descricao': descricao, 'arquivo': SimpleUploadedFile(nome, conteudo, content_type='application/pdf'),
            'classe': self.classe.pk, **extra,
        })

    def test_upload_listagem_e_visualizacao_inline(self):
        outro = get_user_model().objects.create_user('outro')
        self.assertRedirects(self.enviar(adicionado_por=outro.pk), reverse('resolucoes:index'))
        registro = Resolucao.objects.get()
        self.assertEqual(registro.adicionado_por, self.user)
        self.assertEqual(registro.nome_original, 'resolucao.pdf')
        self.assertEqual(registro.tamanho, len(PDF))
        self.assertNotEqual(registro.arquivo.name, registro.nome_original)
        self.assertContains(self.client.get(reverse('resolucoes:index')), 'Visualizar')
        self.assertContains(self.client.get(reverse('home:index')), reverse('resolucoes:index'))
        # Biblioteca compartilhada, como Arquivos gerais.
        self.client.force_login(outro)
        response = self.client.get(reverse('resolucoes:visualizar', args=[registro.pk]))
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response['Content-Disposition'].startswith('inline;'))
        self.assertNotIn('attachment', response['Content-Disposition'])
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertEqual(b''.join(response.streaming_content), PDF)
        with patch('django.db.backends.base.base.BaseDatabaseWrapper.close_if_unusable_or_obsolete'):
            response.close()

    def test_login_obrigatorio_inclusive_acesso_direto_ao_pdf(self):
        self.enviar()
        url = reverse('resolucoes:visualizar', args=[Resolucao.objects.get().pk])
        self.client.logout()
        for response in [self.client.get(reverse('resolucoes:index')), self.enviar(), self.client.get(url)]:
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse('usuarios:login'), response.url)
        self.assertEqual(Resolucao.objects.count(), 1)

    def test_pdf_obrigatorio_extensao_assinatura_e_limite(self):
        for nome, conteudo in [('pagina.html', PDF), ('falso.pdf', b'<html>nao PDF</html>'), ('vazio.pdf', b'')]:
            with self.subTest(nome=nome):
                response = self.enviar(nome=nome, conteudo=conteudo)
                self.assertIn('arquivo', response.context['form'].errors)
        with override_settings(RESOLUCOES_MAX_BYTES=10):
            response = self.enviar()
            self.assertIn('arquivo', response.context['form'].errors)
        response = self.client.post(reverse('resolucoes:index'), {'descricao': ' '})
        self.assertIn('descricao', response.context['form'].errors)
        self.assertIn('arquivo', response.context['form'].errors)
        self.assertFalse(Resolucao.objects.exists())
        self.assertEqual(self.enviar(nome='RESOLUCAO.PDF').status_code, 302)

    def test_busca_por_descricao_arquivo_e_nomes_repetidos(self):
        self.enviar('Alimentos', nome='norma.pdf')
        self.enviar('Farmácias', nome='norma.pdf')
        registros = list(Resolucao.objects.all())
        self.assertNotEqual(registros[0].arquivo.name, registros[1].arquivo.name)
        response = self.client.get(reverse('resolucoes:index'), {'q': 'alimentos'})
        self.assertEqual(response.context['pagina'].paginator.count, 1)
        self.assertEqual(response.context['pagina'][0].descricao, 'Alimentos')
        response = self.client.get(reverse('resolucoes:index'), {'q': 'norma.pdf'})
        self.assertEqual(response.context['pagina'].paginator.count, 2)
        self.assertContains(response, '2 resoluções')
        self.assertContains(self.client.get(reverse('resolucoes:index'), {'q': 'inexistente'}), 'Nenhuma resolução encontrada.')

    def test_paginacao_preserva_busca_e_descricao_escapada(self):
        Resolucao.objects.bulk_create([
            Resolucao(descricao=f'Norma <script>alert(1)</script> {i}', arquivo=f'{i}.pdf',
                      nome_original=f'{i}.pdf', tamanho=1, adicionado_por=self.user) for i in range(26)
        ])
        response = self.client.get(reverse('resolucoes:index'), {'q': 'Norma', 'page': 2})
        self.assertEqual(len(response.context['pagina']), 1)
        self.assertContains(response, '?q=Norma&amp;page=1')
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_pdf_ausente_e_metodo_incorreto(self):
        self.enviar()
        registro = Resolucao.objects.get()
        url = reverse('resolucoes:visualizar', args=[registro.pk])
        self.assertEqual(self.client.post(url).status_code, 405)
        registro.arquivo.delete(save=False)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(reverse('resolucoes:visualizar', args=[registro.pk + 1])).status_code, 404)

    def test_upload_exige_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post(reverse('resolucoes:index'), {
            'descricao': 'Sem token', 'arquivo': SimpleUploadedFile('norma.pdf', PDF),
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Resolucao.objects.exists())

    def test_editar_revogar_e_desmarcar_preserva_pdf_e_autor(self):
        self.enviar()
        registro = Resolucao.objects.get()
        caminho = registro.arquivo.name
        url = reverse('resolucoes:editar', args=[registro.pk])
        self.assertContains(self.client.get(reverse('resolucoes:index')), url)
        self.assertRedirects(self.client.post(url, {'descricao': 'Descrição corrigida', 'classe': self.classe.pk, 'revogada': 'on'}), reverse('resolucoes:index'))
        registro.refresh_from_db()
        self.assertTrue(registro.revogada)
        self.assertEqual(registro.descricao, 'Descrição corrigida')
        self.assertEqual(registro.arquivo.name, caminho)
        self.assertEqual(registro.adicionado_por, self.user)
        response = self.client.get(reverse('resolucoes:index'))
        self.assertContains(response, 'resolucoes-item--revogada')
        self.assertContains(response, '>Revogada</span>')
        self.assertContains(response, reverse('resolucoes:visualizar', args=[registro.pk]))
        self.client.post(url, {'descricao': registro.descricao, 'classe': self.classe.pk})
        registro.refresh_from_db()
        self.assertFalse(registro.revogada)

    def test_descricao_invalida_nao_salva_revogacao(self):
        self.enviar()
        registro = Resolucao.objects.get()
        response = self.client.post(reverse('resolucoes:editar', args=[registro.pk]), {'descricao': ' ', 'classe': self.classe.pk, 'revogada': 'on'})
        self.assertIn('descricao', response.context['form'].errors)
        registro.refresh_from_db()
        self.assertFalse(registro.revogada)
        self.assertEqual(registro.descricao, 'RDC 216 — Boas práticas')

    def test_outro_usuario_nao_edita_nem_exclui(self):
        self.enviar()
        registro = Resolucao.objects.get()
        self.client.force_login(get_user_model().objects.create_user('outro'))
        self.assertNotContains(self.client.get(reverse('resolucoes:index')), reverse('resolucoes:editar', args=[registro.pk]))
        for acao in ['editar', 'excluir']:
            url = reverse(f'resolucoes:{acao}', args=[registro.pk])
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.post(url, {'descricao': 'Mudança', 'revogada': 'on'}).status_code, 403)
        registro.refresh_from_db()
        self.assertFalse(registro.revogada)
        self.assertEqual(registro.descricao, 'RDC 216 — Boas práticas')
        self.assertTrue(registro.arquivo.storage.exists(registro.arquivo.name))

    def test_administrador_pode_editar_resolucao_de_outro(self):
        self.enviar()
        registro = Resolucao.objects.get()
        admin = get_user_model().objects.create_user('admin', is_superuser=True)
        self.client.force_login(admin)
        url = reverse('resolucoes:editar', args=[registro.pk])
        self.assertContains(self.client.get(reverse('resolucoes:index')), url)
        self.assertEqual(self.client.post(url, {'descricao': 'Revisada', 'classe': self.classe.pk, 'revogada': 'on'}).status_code, 302)
        registro.refresh_from_db()
        self.assertTrue(registro.revogada)
        self.assertEqual(registro.adicionado_por, self.user)

    def test_exclusao_so_no_post_e_pdf_so_apos_commit(self):
        self.enviar()
        registro = Resolucao.objects.get()
        arquivo = registro.arquivo
        url = reverse('resolucoes:excluir', args=[registro.pk])
        self.assertContains(self.client.get(url), 'Confirmar exclusão')
        self.assertTrue(Resolucao.objects.filter(pk=registro.pk).exists())
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            self.assertRedirects(self.client.post(url), reverse('resolucoes:index'))
        self.assertFalse(Resolucao.objects.exists())
        self.assertTrue(arquivo.storage.exists(arquivo.name))
        self.assertEqual(len(callbacks), 1)
        callbacks[0]()
        self.assertFalse(arquivo.storage.exists(arquivo.name))

    def test_administrador_exclui_e_pdf_ausente_nao_impede_exclusao(self):
        self.enviar()
        registro = Resolucao.objects.get()
        registro.arquivo.delete(save=False)
        self.client.force_login(get_user_model().objects.create_user('admin', is_superuser=True))
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('resolucoes:excluir', args=[registro.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Resolucao.objects.exists())

    def test_edicao_e_exclusao_exigem_login_e_csrf(self):
        self.enviar()
        registro = Resolucao.objects.get()
        protegido = Client(enforce_csrf_checks=True)
        protegido.force_login(self.user)
        self.client.logout()
        for acao in ['editar', 'excluir']:
            url = reverse(f'resolucoes:{acao}', args=[registro.pk])
            self.assertEqual(self.client.get(url).status_code, 302)
            self.assertEqual(self.client.post(url).status_code, 302)
            self.assertEqual(protegido.post(url, {'descricao': 'Mudança'}).status_code, 403)
        self.assertTrue(Resolucao.objects.filter(pk=registro.pk).exists())

    def test_nova_classe_disponivel_para_todos_e_reutilizada(self):
        self.assertRedirects(self.enviar(classe='nova', nova_classe='  Saúde   ocupacional  '), reverse('resolucoes:index'))
        classe = ClasseResolucao.objects.get(chave='saude ocupacional')
        self.assertEqual(classe.nome, 'Saúde ocupacional')
        self.assertEqual(Resolucao.objects.get().classe, classe)
        self.client.force_login(get_user_model().objects.create_user('outro'))
        response = self.client.get(reverse('resolucoes:index'))
        for form in [response.context['form'], response.context['filtro']]:
            self.assertIn((str(classe.pk), classe.nome), list(form.fields['classe'].choices))
        for nome in ['SAUDE OCUPACIONAL', 'saúde  ocupacional', 'Saude Ocupacional']:
            self.assertEqual(self.enviar(classe='nova', nova_classe=nome).status_code, 302)
        self.assertEqual(ClasseResolucao.objects.filter(chave='saude ocupacional').count(), 1)
        self.assertEqual(Resolucao.objects.filter(classe=classe).count(), 4)

    def test_servicos_de_alimentos_reaproveita_alimentos(self):
        quantidade = ClasseResolucao.objects.count()
        self.assertEqual(self.enviar(classe='nova', nova_classe=' SERVIÇOS de ALIMENTOS ').status_code, 302)
        self.assertEqual(Resolucao.objects.get().classe, self.classe)
        self.assertEqual(ClasseResolucao.objects.count(), quantidade)

    def test_classe_obrigatoria_e_invalida_sem_gravar_classe_nem_resolucao(self):
        quantidade = ClasseResolucao.objects.count()
        for dados, campo in [
            ({'classe': ''}, 'classe'),
            ({'classe': '99999999999999999999999999'}, 'classe'),
            ({'classe': 'nova', 'nova_classe': ' '}, 'nova_classe'),
            ({'classe': 'nova', 'nova_classe': 'x' * 121}, 'nova_classe'),
            ({'nova_classe': 'Nova categoria'}, 'nova_classe'),
            ({'classe': 'nova', 'nova_classe': 'Nova categoria', 'conteudo': b'invalido'}, 'arquivo'),
        ]:
            with self.subTest(dados=dados):
                response = self.enviar(**dados)
                self.assertIn(campo, response.context['form'].errors)
        self.assertEqual(ClasseResolucao.objects.count(), quantidade)
        self.assertFalse(Resolucao.objects.exists())

    def test_edicao_classifica_legado_e_preserva_arquivo(self):
        self.enviar()
        registro = Resolucao.objects.get()
        Resolucao.objects.filter(pk=registro.pk).update(classe=None)
        url = reverse('resolucoes:editar', args=[registro.pk])
        response = self.client.post(url, {'descricao': registro.descricao, 'classe': 'nova', 'nova_classe': 'Saúde do trabalhador'})
        self.assertRedirects(response, reverse('resolucoes:index'))
        atualizado = Resolucao.objects.get(pk=registro.pk)
        self.assertEqual(atualizado.classe.nome, 'Saúde do trabalhador')
        self.assertEqual(atualizado.arquivo.name, registro.arquivo.name)
        self.assertEqual(atualizado.adicionado_por, self.user)
        self.assertEqual(self.client.get(url).context['form'].initial['classe'], str(atualizado.classe_id))

    def test_filtros_combinados_classe_situacao_busca_e_legado(self):
        saude = ClasseResolucao.objects.get(chave='servicos de saude')
        self.enviar('Norma de alimentos')
        alimentos = Resolucao.objects.get()
        self.enviar('Norma sanitária', classe=saude.pk)
        sanitaria = Resolucao.objects.exclude(pk=alimentos.pk).get()
        Resolucao.objects.filter(pk=alimentos.pk).update(revogada=True)
        self.enviar('Norma antiga')
        legado = Resolucao.objects.get(descricao='Norma antiga')
        Resolucao.objects.filter(pk=legado.pk).update(classe=None)
        casos = [
            ({'situacao': 'revogadas'}, [alimentos.pk]),
            ({'situacao': 'nao_revogadas'}, [legado.pk, sanitaria.pk]),
            ({'classe': saude.pk}, [sanitaria.pk]),
            ({'classe': 'sem_classe'}, [legado.pk]),
            ({'q': 'Norma', 'classe': self.classe.pk, 'situacao': 'revogadas'}, [alimentos.pk]),
            ({'q': 'inexistente', 'classe': self.classe.pk, 'situacao': 'revogadas'}, []),
            ({'classe': self.classe.pk, 'situacao': 'nao_revogadas'}, []),
        ]
        for filtros, ids in casos:
            with self.subTest(filtros=filtros):
                response = self.client.get(reverse('resolucoes:index'), filtros)
                self.assertEqual([r.pk for r in response.context['pagina']], ids)
        for filtros in [{'situacao': 'invalida'}, {'classe': '999999999999999999999999999'}]:
            response = self.client.get(reverse('resolucoes:index'), filtros)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['filtro'].errors)
            self.assertEqual(response.context['pagina'].paginator.count, 0)

    def test_paginacao_preserva_todos_filtros_e_ids_html_distintos(self):
        Resolucao.objects.bulk_create([
            Resolucao(descricao=f'Norma {i}', arquivo=f'{i}.pdf', classe=self.classe, revogada=True,
                      nome_original=f'{i}.pdf', tamanho=1, adicionado_por=self.user) for i in range(26)
        ])
        response = self.client.get(reverse('resolucoes:index'), {
            'q': 'Norma', 'classe': self.classe.pk, 'situacao': 'revogadas', 'page': 2})
        self.assertEqual(len(response.context['pagina']), 1)
        self.assertContains(response, f'?q=Norma&amp;classe={self.classe.pk}&amp;situacao=revogadas&amp;page=1')
        self.assertContains(response, 'id="id_classe"', count=1)
        self.assertContains(response, 'id="filtro_classe"', count=1)
        self.assertContains(response, 'id="filtro_situacao"', count=1)
