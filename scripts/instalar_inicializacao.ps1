param([Parameter(Mandatory=$true)][string]$TaskUser)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$taskName = 'Sistema VISA 2 - Servidor 8282'
$pythonPath = Join-Path $projectRoot 'venv\Scripts\python.exe'
$entryPath = Join-Path $projectRoot 'scripts\servidor.py'
$logFolder = Join-Path $projectRoot 'logs'
New-Item -ItemType Directory -Path $logFolder -Force | Out-Null
try {
    $action = New-ScheduledTaskAction -Execute $pythonPath -Argument ('"' + $entryPath + '"') -WorkingDirectory $projectRoot
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $trigger.Delay = 'PT30S'
    # Executa sem login e sem guardar senha Windows, com privilégios limitados do usuário.
    $principal = New-ScheduledTaskPrincipal -UserId $TaskUser -LogonType S4U -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) `
        -MultipleInstances IgnoreNew -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
        -Principal $principal -Settings $settings -Description 'Servidor Django/Waitress na porta 8282, iniciado ao ligar o computador.' -Force | Out-Null
    Start-ScheduledTask -TaskName $taskName
    'Tarefa registrada e iniciada.' | Set-Content -LiteralPath (Join-Path $logFolder 'instalacao.txt') -Encoding UTF8
} catch {
    $_.Exception.Message | Set-Content -LiteralPath (Join-Path $logFolder 'instalacao.txt') -Encoding UTF8
    exit 1
}
