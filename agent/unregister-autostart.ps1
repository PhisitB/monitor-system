# Remove the MonitorAgent scheduled task.

schtasks /delete /tn "MonitorAgent" /f
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host "MonitorAgent task removed successfully." -ForegroundColor Green
} else {
    Write-Host "Failed to remove MonitorAgent task (exit code $exitCode)." -ForegroundColor Red
}
exit $exitCode
