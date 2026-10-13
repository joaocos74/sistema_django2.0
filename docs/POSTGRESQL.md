# PostgreSQL

## Configuração

O driver usado é psycopg 3. O arquivo `.env` é carregado automaticamente; variáveis do processo têm precedência. Copie `.env.example` para `.env` e informe um banco vazio, usuário e senha próprios do sistema. A senha não deve ser enviada ao Git ou ao chat.

Configure `DB_ENGINE=postgresql` para ativar o PostgreSQL. PostgreSQL é o padrão. SQLite só é ativado explicitamente com DB_ENGINE=sqlite. Uma falha de conexão PostgreSQL não provoca retorno automático ao SQLite.

Crie o banco e o usuário pelo pgAdmin, deixando esse usuário como proprietário do banco. Para rodar testes, o usuário precisa de permissão CREATEDB, ou de um banco de testes preparado pelo administrador. Não execute testes apontando um nome de banco de testes que contenha dados reais.

## Instalação zerada (configuração atual)

O banco configurado é `sistema_visa2.0`, em `127.0.0.1:5433`. As migrações foram aplicadas sem importar registros do SQLite. Para instalar do zero, use `python manage.py migrate` e depois `python manage.py createsuperuser`. Reinicie o servidor Django depois de mudar o `.env`.

## Transferência opcional de dados antigos (não utilizada)

1. Pare o servidor Django e qualquer processo que grave dados antes da transferência.
2. Preserve `media/` e `arquivos_privados/`: anexos não são armazenados dentro do banco.
3. Instale as dependências: `venv\Scripts\python.exe -m pip install -r requirements.txt`.
4. Antes de alterar o `.env`, pode preparar um backup: `venv\Scripts\python.exe manage.py migrar_postgresql --prepare-only`.
5. Configure a conexão PostgreSQL em `.env`.
6. Execute `venv\Scripts\python.exe manage.py migrar_postgresql`.
7. Execute `venv\Scripts\python.exe manage.py check --database default` e `venv\Scripts\python.exe manage.py test`.
8. Confira login, cadastros, anexos, geração de notificações e Excel antes de reabrir o uso do sistema.

O comando cria uma cópia consistente do SQLite e exporta os dados para `backups/`. Recusa destinos com dados, aplica as migrações, importa usuários e dados com suas chaves, e confere contagens por modelo. A importação é transacional; uma falha reverte os dados importados. Permissões e content types padrão são recriados pelas migrações. O loaddata ajusta as sequências de IDs; a sequência anual de notificações é transferida como registro comum.

Os backups contêm informações do sistema, inclusive hashes de senha, e devem ser guardados com acesso restrito. Não apague o SQLite original após a migração. Se voltar a ele, estará usando o estado anterior à transferência, sem as alterações posteriores feitas no PostgreSQL.

## Testes

Os testes automatizados foram mantidos: verificam permissões, emissão sequencial, anexos e exportações, e não executam durante o uso normal. `manage.py test` cria um banco de teste separado.
