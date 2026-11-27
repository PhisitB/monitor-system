# Remove the MonitorAgent scheduled task.

schtasks /delete /tn "MonitorAgent" /f

if ($LASTEXITCODE -eq 0) {
    Write-Host "MonitorAgent task removed successfully." -ForegroundColor Green
} else {
    Write-Host "Failed to remove MonitorAgent task (exit code $LASTEXITCODE)." -ForegroundColor Red
}
