# Uni Mail Assistant - setup for Windows (BETA). Started by setup.bat.
# Passwords go into Windows Credential Manager, never into files.
# "Continue": harmless warnings from Python/pip must not stop the setup; real errors are checked via $LASTEXITCODE
$ErrorActionPreference = "Continue"
$Dir = Split-Path -Parent $PSScriptRoot
Set-Location $Dir
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

Write-Host "`nUni Mail Assistant - setup (Windows, beta)" -ForegroundColor Cyan
Write-Host "Everything stays on this PC. Passwords go into Windows Credential Manager."

# ---- 1. Python
$Py = $null
foreach ($c in @("py", "python")) {
    try {
        $p = & $c -c "import sys; print(sys.executable) if sys.version_info >= (3, 9) else sys.exit(1)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $p) { $Py = $p.Trim(); break }
    } catch {}
}
if (-not $Py) {
    Write-Host "Python 3 is needed. Install it from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "IMPORTANT: tick 'Add python.exe to PATH' in the installer. Then double-click setup.bat again."
    exit 1
}
Set-Content -Path ".python-path" -Value $Py -Encoding ASCII
Write-Host "  OK  Python: $Py"

# ---- 2. keyring (Windows Credential Manager) + truststore (use Windows' own certificate checking,
#         needed on PCs with antivirus HTTPS scanning, company/school networks or VPNs)
& $Py -m pip install --user --quiet --disable-pip-version-check --upgrade keyring truststore
if ($LASTEXITCODE -ne 0) { Write-Host "Could not install 'keyring'/'truststore'. Check your internet connection." -ForegroundColor Red; exit 1 }
Write-Host "  OK  Secure password storage and certificate checking installed"

# ---- 3. questions
& $Py wizard.py
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "`nChecking everything" -ForegroundColor Cyan
& $Py helper.py check
if ($LASTEXITCODE -ne 0) { Write-Host "Fix the line marked with X above, then run setup.bat again." -ForegroundColor Yellow; exit 1 }

Write-Host "`nFirst check of your inbox - this can take a few minutes..." -ForegroundColor Cyan
& $Py helper.py sync

# ---- 4. background tasks + desktop shortcut
& "$PSScriptRoot\service.ps1" on

$Pyw = Join-Path (Split-Path $Py) "pythonw.exe"
if (-not (Test-Path $Pyw)) { $Pyw = $Py }
$Shell = New-Object -ComObject WScript.Shell
$Lnk = $Shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath("Desktop")) "Uni Mail Assistant.lnk"))
$Lnk.TargetPath = $Pyw
$Lnk.Arguments = "`"$Dir\app.py`""
$Lnk.WorkingDirectory = $Dir
$Lnk.Save()

Write-Host "`nDone!" -ForegroundColor Green
Write-Host "- It checks every 15 minutes while your PC is on (and starts by itself after a restart)."
Write-Host "- Chat window: 'Uni Mail Assistant' on your Desktop."
Write-Host "- Change anything later: double-click setup.bat again. Remove everything: windows\uninstall.bat"
