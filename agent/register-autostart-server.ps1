# Register MonitorAgent with Windows Task Scheduler for a server (e.g. a VPS)
# where nobody stays logged on: starts at boot and runs whether the user is
# logged on or not (S4U: no password stored, no network-share access needed).
# Run from an elevated PowerShell. Safe to re-run — /f overwrites the task.
# Remove with agent\unregister-autostart.ps1.

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$pythonw     = Join-Path $projectRoot ".venv\Scripts\pythonw.exe"
$envFile     = Join-Path $projectRoot ".env"

$isAdmin = ([System.Security.Principal.WindowsPrincipal][System.Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [System.Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: run this script from an elevated PowerShell (Run as administrator)." -ForegroundColor Red
    Write-Host "A boot-time task that runs without a logged-on user needs admin rights to register." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $pythonw)) {
    Write-Host "ERROR: pythonw.exe not found at $pythonw" -ForegroundColor Red
    Write-Host "Make sure the virtual environment exists (.venv\Scripts\pythonw.exe)." -ForegroundColor Red
    exit 1
}

# Without a unique DEVICE_ID this server would overwrite another machine's row in Supabase.
$deviceLine = if (Test-Path $envFile) { Select-String -Path $envFile -Pattern '^\s*DEVICE_ID\s*=\s*\S' | Select-Object -First 1 }
if (-not $deviceLine) {
    Write-Host "ERROR: set a unique DEVICE_ID in $envFile (e.g. DEVICE_ID=vps)." -ForegroundColor Red
    exit 1
}

$tempXml = Join-Path ([System.IO.Path]::GetTempPath()) "MonitorAgent-$([guid]::NewGuid()).xml"
$pythonwXml     = [System.Security.SecurityElement]::Escape($pythonw)
$projectRootXml = [System.Security.SecurityElement]::Escape($projectRoot)
$userXml        = [System.Security.SecurityElement]::Escape([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)

@"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Starts the Monitor System local agent (agent.py) at boot (server mode).</Description>
    <URI>\MonitorAgent</URI>
  </RegistrationInfo>
  <Triggers>
    <BootTrigger>
      <Enabled>true</Enabled>
      <Delay>PT1M</Delay>
    </BootTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$userXml</UserId>
      <LogonType>S4U</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$pythonwXml</Command>
      <Arguments>-u agent/agent.py</Arguments>
      <WorkingDirectory>$projectRootXml</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@ | Out-File -FilePath $tempXml -Encoding Unicode

schtasks /create /xml "$tempXml" /tn "MonitorAgent" /f
$exitCode = $LASTEXITCODE

Remove-Item $tempXml -ErrorAction SilentlyContinue

if ($exitCode -eq 0) {
    Write-Host "MonitorAgent task registered (server mode)." -ForegroundColor Green
    Write-Host "The agent will start 1 minute after boot, even when nobody is logged on."
    Write-Host "Start it now with: schtasks /run /tn MonitorAgent"
    Write-Host "Log file: $(Join-Path $projectRoot 'agent\agent.log')"
} else {
    Write-Host "Failed to register MonitorAgent task (exit code $exitCode)." -ForegroundColor Red
}
exit $exitCode
