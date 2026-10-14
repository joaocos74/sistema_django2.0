# Inicialização automática no Windows

O sistema é servido pelo Waitress na porta 8282. A tarefa **Sistema VISA 2 - Servidor 8282** inicia após o boot, com atraso de 30 segundos, sem exigir terminal ou login interativo. Usa a conta configurada com privilégios limitados e autenticação S4U (sem guardar a senha do Windows).

Acesse http://127.0.0.1:8282/. O servidor escuta nas interfaces de rede; acesso por outro computador depende de `DJANGO_ALLOWED_HOSTS` no `.env` e das regras de firewall da máquina.

- Entrada: `scripts/servidor.py`.
- Logs: `logs/servidor.log`, com rotação e até cinco cópias.
- Se falhar, o Agendador tenta reiniciar em um minuto.
- O servidor aguarda o PostgreSQL ficar disponível por até dois minutos.
- A pasta do projeto e o ambiente `venv` precisam permanecer no caminho registrado.
- `.env` contém a configuração local. O modo automático utiliza a configuração atual, com DEBUG desativado e chave privada.

No Agendador de Tarefas é possível iniciar, encerrar ou desabilitar essa tarefa. Após alterar código ou `.env`, encerre e inicie a tarefa para carregar as mudanças. Após alterar CSS, JavaScript ou imagens, execute também:

```powershell
.\venv\Scripts\python.exe manage.py collectstatic --noinput
```

Para reinstalar a tarefa, execute em PowerShell como administrador (substituindo a conta quando necessário):

```powershell
.\scripts\instalar_inicializacao.ps1 -TaskUser 'COMPUTADOR\USUARIO'
```

Para mudar de computador, recrie o ambiente virtual, configure o PostgreSQL e o `.env`, aplique as migrações, colete os estáticos e registre a tarefa novamente. O PostgreSQL deve estar configurado para inicialização automática no Windows.
