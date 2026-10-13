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
- `redesim/`: pesquisa de cadastros por CNPJ/CPF, lançamento de liberações e exportação do histórico.
- `denuncias/`: registro, consulta, atribuição de fiscal e acompanhamento de denúncias.

## Redesim e Denúncias

Após atualizar o código, execute `python manage.py migrate` com o ambiente virtual ativo.
Os dois módulos estão no menu inicial.

Na Redesim, pesquise um CNPJ/CPF já cadastrado. Qualquer usuário autenticado pode
salvar a liberação, independentemente do fiscal responsável. A operação atualiza apenas o alvará e as observações
da última fiscalização e guarda uma cópia dos dados no histórico Redesim, sem alterar
nome, documento, fiscal ou classificação do estabelecimento. O histórico é listado
automaticamente do lançamento mais recente ao mais antigo. Documentos não encontrados
geram um aviso, sem criar cadastros. É necessário existir uma fiscalização para atualizar.
Não consulta serviços externos.

Em Denúncias, a busca preenche os dados do cadastro. O vínculo também é verificado no
servidor ao salvar, ignorando a pontuação do documento. Documentos duplicados devem ser
regularizados antes do vínculo. Locais sem cadastro podem ter denúncias sem vínculo;
depois de cadastrar o estabelecimento, abra e salve a denúncia para vinculá-la pelo
documento. Um vínculo já existente é preservado nas edições.

O autor, o fiscal designado e o administrador podem editar a denúncia. Outros usuários
autenticados podem consultar. Em Analisar, o bloco “Histórico de denúncias” mostra os
registros do estabelecimento e permite abrir ou registrar uma denúncia. Atribuir um
fiscal à denúncia não troca o fiscal do estabelecimento.

As novas apps usam o banco desta versão. Dados da aplicação antiga não são importados
automaticamente. Os riscos anteriores estão em `ANALISE_SEGURANCA.txt`.

Dados do estabelecimento em denúncias vinculadas são somente leitura. Novas denúncias
recebem esses dados do cadastro; nas edições, os dados já registrados são preservados.
O servidor ignora alterações desses campos enviadas pelo navegador.

Em Estatísticas, os blocos de Denúncias e Redesim usam os filtros de ano e fiscal e
integram o PDF consolidado. Denúncias usam a data da denúncia (ou a data de criação
quando ausente), o fiscal designado e o status atual. Incluem locais sem cadastro.
Redesim usa a data de liberação, o usuário que lançou e a classificação guardada no
histórico. Conta estabelecimentos distintos e lançamentos separadamente. Um mesmo
local pode aparecer em vários grupos; a soma dos grupos não é o total anual distinto.
Lançamentos Redesim sem data de liberação não entram nas estatísticas anuais.

Templates, CSS e JavaScript permanecem dentro de seus respectivos aplicativos.

## Verificação e próximos trabalhos

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

O arquivo `sistema_django_visa-main.zip` é a referência da versão anterior e não integra este repositório. Após salvar esta base no GitHub, retomar a comparação com essa referência e os ajustes de frontend. A organização inicial não altera telas nem regras de negócio.
