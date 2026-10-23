# Resoluções

App `resolucoes`: biblioteca compartilhada de PDFs para consulta, disponível em
Home → Resoluções (`/resolucoes/`). Segue o acesso de Arquivos gerais: usuários
autenticados podem adicionar e visualizar documentos.

O formulário reúne arquivo PDF, descrição e Adicionar. A pesquisa procura na
descrição e no nome original, com 25 registros por página. Visualizar abre uma
nova aba e responde com `application/pdf` e `Content-Disposition: inline`, sem
forçar download. O navegador precisa estar configurado para abrir PDFs; suas
preferências podem optar por baixá-los. Não há bloqueio de cópia ou impressão.

O autor ou superusuário pode acessar Editar para corrigir a descrição e marcar
ou desmarcar a opção Revogada. Documentos revogados continuam consultáveis,
com fundo/textos vermelhos e identificação textual de situação. Nenhuma
revogação é presumida: o usuário responsável informa a situação.

Excluir resolução fica dentro da edição e abre uma confirmação. A exclusão
ocorre somente por POST autenticado com CSRF e autorização do autor ou
superusuário. O PDF é removido depois do commit da exclusão no banco.

O envio aceita arquivos de até 25 MiB com extensão `.pdf` e identificação `%PDF-`.
Essa conferência de formato não é um antivírus nem uma validação integral do PDF.
O autor vem da sessão e os arquivos recebem nomes UUID para evitar sobrescrita.

- Tabela: `resolucoes_resolucao` (descrição, revogada, arquivo, nome original, tamanho,
  autor e data de inclusão).
- Relação: `adicionado_por_id` → `auth_user.id`, com `PROTECT` no Django.
- PDFs: `arquivos_privados/resolucoes/`, já abrangidos pelo backup de
  `arquivos_privados/`. A pasta não é publicada como mídia estática.
- Visualização: `/resolucoes/<id>/visualizar/`, com login obrigatório,
  `nosniff` e cache privado desativado.
- Modelos e armazenamento: `models.py`; validação: `forms.py`; cadastro,
  pesquisa e resposta PDF: `views.py`; layout: `templates/` e `static/`.

Instalação/atualização: aplicar migrações, executar `collectstatic` e reiniciar
o servidor. Não há importação automática de sites ou resoluções pré-carregadas.
