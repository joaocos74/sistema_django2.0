# Número da pasta física

O número exibido nas pesquisas, no cronograma, nas atribuições, no REDESIM,
nas denúncias, no Auto / Termo e no consolidado Excel é `numero_pasta`.
O ID interno permanece fixo nas URLs e nos vínculos do banco. Nunca renumere
as chaves primárias ou as chaves estrangeiras para mudar uma pasta.

## Uso

- Na primeira atualização, cada cadastro recebe como número da pasta seu ID atual.
- Novos cadastros recebem o maior número de pasta entre os estabelecimentos ativos
  mais 1. Sem ativos, recebem 1. Números de inativos e o maior número histórico não
  determinam a próxima pasta. Por exemplo: após inativar a pasta 1 e mudar a pasta 6
  para 1, os ativos ficam de 1 a 5 e o novo cadastro recebe 6. Lacunas no meio da
  numeração não são preenchidas automaticamente.
- O superusuário altera o número em **Analisar → Pasta → Numeração e histórico**.
- É possível reutilizar a pasta de um cadastro inativo. Dois ativos não podem
  ocupar a mesma pasta. Para reativar um cadastro cuja pasta foi reutilizada,
  primeiro atribua a ele outro número disponível.
- O fiscal, os documentos e os demais vínculos permanecem no estabelecimento
  original. Reutilizar a pasta não transfere esses vínculos ao novo ocupante.
- Pesquisar mostra os ativos por padrão, em ordem crescente de pasta. O filtro
  **Status do Cadastro** permite consultar inativos ou todos. O cronograma mostra ativos.
- O histórico registra atribuição inicial, trocas de número e mudanças de situação,
  com data e usuário quando disponível. Registros migrados aparecem como “Sistema”.
- O campo 03 do Auto / Termo acompanha a pasta atual e não aceita um padrão manual
  diferente. O conteúdo das notificações já geradas permanece preservado.
- O Excel inclui ativos e inativos. O número da pasta aparece na tabela principal
  e nas abas vinculadas. As referências internas também permanecem no arquivo,
  identificadas/documentadas para cruzar históricos sem confundir pastas reutilizadas.

## Atualização de outra instalação

Depois de publicar esta versão no GitHub, faça backup do PostgreSQL, encerre a
tarefa **Sistema VISA 2 - Servidor 8282** e execute na pasta do projeto:

```powershell
git pull --ff-only origin main
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py collectstatic --noinput
.\venv\Scripts\python.exe manage.py check
```

Inicie novamente a tarefa. A migração `register.0010_numero_pasta` preserva os
cadastros existentes e inicializa a sequência e o histórico.

## Manutenção do código

Criações e alterações de número/situação devem passar por `Estabelecimento.save()`.
Esse método serializa a reserva da sequência e grava o histórico na mesma transação.
Não use `QuerySet.update()` ou `bulk_create()` nesses fluxos: eles não executam o
método `save()`. A restrição do banco continua impedindo pastas duplicadas entre ativos.
