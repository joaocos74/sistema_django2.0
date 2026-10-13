# Sistema Django 2.0

Nova versão do sistema de Vigilância Sanitária, em desenvolvimento. O trabalho atual está na etapa de ajustes do frontend.

## Executar no Windows (PowerShell)

O ambiente conferido neste computador usa Python 3.14.7. As versões das dependências estão fixadas em `requirements.txt`.

```powershell
git clone https://github.com/joaocos74/sistema_django2.0.git
cd sistema_django2.0
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

Acesse http://127.0.0.1:8000/. Na pasta atual, o ambiente existente se chama `venv`; use esse nome no lugar de `.venv` para aproveitá-lo. Em outro computador, recrie o ambiente em vez de copiar sua pasta.

## Configuração e dados locais

Por padrão, o sistema inicia em modo de desenvolvimento, com uma chave pública exclusiva para esse uso. Para definir uma chave própria no PowerShell:

```powershell
$env:DJANGO_SECRET_KEY = 'substitua-por-uma-chave-aleatoria-privada'
$env:DJANGO_DEBUG = 'true'
$env:DJANGO_ALLOWED_HOSTS = 'localhost,127.0.0.1'
```

As configurações são lidas das variáveis de ambiente; arquivos `.env` não são carregados automaticamente. Publicar o código no GitHub não coloca o sistema em produção. Uma implantação requer configuração própria, incluindo `DJANGO_DEBUG=false` e uma chave privada.

O banco `db.sqlite3` e os documentos em `media/` ficam somente no computador e não são enviados ao GitHub. Faça backup separado desses dois itens para preservar cadastros, usuários e anexos. As migrações ficam versionadas para criar um banco vazio em outro ambiente.

## Estrutura

- `app/`: configurações e rotas principais.
- `register/`: estabelecimentos, fiscalização, documentos e telas relacionadas.
- `home/`: página inicial e agenda.
- `usuarios/`: autenticação e gestão de usuários.

Templates, CSS e JavaScript permanecem dentro de seus respectivos aplicativos.

## Verificação e próximos trabalhos

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

O arquivo `sistema_django_visa-main.zip` é a referência da versão anterior e não integra este repositório. Após salvar esta base no GitHub, retomar a comparação com essa referência e os ajustes de frontend. A organização inicial não altera telas nem regras de negócio.
