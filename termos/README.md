# Termos e notificações

Esta app concentra formulários, preenchimento cadastral, templates, impressão, padrões personalizados e emissão de notificações.

- `forms.py`: campos permitidos e limites de tamanho.
- `contexto.py`: preenchimento com dados atuais do estabelecimento e responsáveis.
- `services.py`: sequência anual global e emissão transacional.
- `views.py`: permissões, padrões, emissão e histórico.
- `templates/termos` e `static/termos`: apresentação e impressão.

Abrir uma Notificação mostra a próxima numeração sem reservar. Gerar atribui o número definitivo segundo o ano atual em America/Sao_Paulo, salva uma cópia dos campos e atualiza o padrão do estabelecimento na mesma transação. O número não é editável. Prévia desatualizada recebe o próximo número disponível. O token de emissão evita duplicação ao repetir uma requisição e vale por 24 horas. Se o banco estiver ocupado, a operação pode ser repetida com o mesmo token.

Os documentos emitidos são consultados e reimpressos pelo histórico; não há alteração ou exclusão pela interface. O padrão continua independente do Auto Termo. A data editável no corpo não controla o ano da sequência. As notificações anteriores a esta funcionalidade eram apenas padrões e não são convertidas em emissões numeradas.

Somente o fiscal da última fiscalização e administradores podem salvar ou gerar. Usuários autenticados podem consultar, conforme a regra de consulta dos estabelecimentos.

As migrações adotam as tabelas existentes `register_autotermopadrao` e `register_notificacaopadrao` sem apagar seus dados. Os nomes físicos foram preservados deliberadamente; os modelos pertencem agora a `termos`. As URLs antigas de documentos em `register` continuam compatíveis.

Validação: `python manage.py test termos`.
