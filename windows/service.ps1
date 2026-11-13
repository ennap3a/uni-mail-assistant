# Background tasks for Windows (BETA).
#   service.ps1 on      -> check mail every 15 min + Telegram listener (if Telegram is on)
#   service.ps1 off     -> remove the tasks
#   service.ps1 status
param([string]$Mode = "status")
$Dir = Split-Path -Parent $PSScriptRoot
$Py = (Get-Content (Join-Path $Dir ".python-path") -ErrorAction SilentlyContinue)
if (-not $Py) { $Py = "python" }
$Pyw = Join-Path (Split-Path $Py) "pythonw.exe"
if (-not (Test-Path $Pyw)) { $Pyw = $Py }
$SyncTask = "UniMailAssistant-Sync"
$ListenTask = "UniMailAssistant-Telegram"

function TelegramOn {
    try {
        $c = Get-Content (Join-Path $Dir "config.json") -Raw -Encoding UTF8 | ConvertFrom-Json
        return ($c.outputs.telegram.enabled -and ($c.outputs.telegram.listen -ne $false))
    } catch { return $false }
}

switch ($Mode) {
    "on" {
        $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew
        $action = New-ScheduledTaskAction -Execute $Pyw -Argument "`"$Dir\helper.py`" sync" -WorkingDirectory $Dir
        $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 15)
        Register-ScheduledTask -TaskName $SyncTask -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
        Write-Host "  OK  Checks every 15 minutes while your PC is on."
        if (TelegramOn) {
            $ls = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
                  -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)
            $la = New-ScheduledTaskAction -Execute $Pyw -Argument "`"$Dir\helper.py`" listen" -WorkingDirectory $Dir
            Register-ScheduledTask -TaskName $ListenTask -Action $la -Trigger (New-ScheduledTaskTrigger -AtLogOn) -Settings $ls -Force | Out-Null
            Start-ScheduledTask -TaskName $ListenTask
            Write-Host "  OK  Telegram: buttons and questions are answered right away."
        }
    }
    "off" {
        foreach ($t in @($SyncTask, $ListenTask)) { Unregister-ScheduledTask -TaskName $t -Confirm:$false -ErrorAction SilentlyContinue }
        Write-Host "  Stopped."
    }
    default {
        foreach ($t in @($SyncTask, $ListenTask)) {
            $task = Get-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue
            if ($task) { Write-Host "  $t : $($task.State)" } else { Write-Host "  $t : not installed" }
        }
        Get-Content (Join-Path $Dir "activity.log") -Tail 5 -ErrorAction SilentlyContinue
    }
}
