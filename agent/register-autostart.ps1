# Register MonitorAgent task with Windows Task Scheduler.
# Generates the task XML at runtime so paths are always correct for the
# current machine — no hardcoded username or path in the repo.
# Safe to re-run — /f overwrites any existing task with the same name.

# Resolve project root (parent of the agent/ directory this script lives in).
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$pythonw     = Join-Path $projectRoot ".venv\Scripts\pythonw.exe"

if (-not (Test-Path $pythonw)) {
    Write-Host "ERROR: pythonw.exe not found at $pythonw" -ForegroundColor Red
    Write-Host "Make sure the virtual environment exists (.venv\Scripts\pythonw.exe)." -ForegroundColor Red
    exit 1
}

# Write task XML to a temp file (paths resolved to this machine).
$tempXml = Join-Path ([System.IO.Path]::GetTempPath()) "MonitorAgent-$([guid]::NewGuid()).xml"
# Escape &, <, > etc. so unusual folder names cannot break the XML.
$pythonwXml     = [System.Security.SecurityElement]::Escape($pythonw)
$projectRootXml = [System.Security.SecurityElement]::Escape($projectRoot)
# Bind trigger and principal to the current user: a logon trigger without a
# UserId fires for any user and needs admin rights to register.
$userXml = [System.Security.SecurityElement]::Escape([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)

@"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Starts the Monitor System local agent (agent.py) on user logon.</Description>
    <URI>\MonitorAgent</URI>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <Delay>PT30S</Delay>
      <UserId>$userXml</UserId>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$userXml</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>false</StartWhenAvailable>
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
    Write-Host "MonitorAgent task registered successfully." -ForegroundColor Green
    Write-Host "The agent will start automatically 30 seconds after you log on."
    Write-Host "Command: $pythonw -u agent/agent.py"
    Write-Host "Working directory: $projectRoot"
    Write-Host "Log file: $(Join-Path $projectRoot 'agent\agent.log')"
} else {
    Write-Host "Failed to register MonitorAgent task (exit code $exitCode)." -ForegroundColor Red
}
exit $exitCode
