# PowerShell script to stop Gradle daemons and clear cache
Write-Host "Stopping Gradle daemons..." -ForegroundColor Yellow
cd $PSScriptRoot
.\gradlew --stop

Write-Host "`nClearing Gradle cache..." -ForegroundColor Yellow
$gradleCache = "$env:USERPROFILE\.gradle\caches"
if (Test-Path $gradleCache) {
    Remove-Item -Path $gradleCache -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "✓ Cleared Gradle cache" -ForegroundColor Green
}

Write-Host "`nClearing project build folders..." -ForegroundColor Yellow
if (Test-Path ".gradle") {
    Remove-Item -Path ".gradle" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "✓ Cleared .gradle folder" -ForegroundColor Green
}
if (Test-Path "app\build") {
    Remove-Item -Path "app\build" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "✓ Cleared app\build folder" -ForegroundColor Green
}

Write-Host "`n✓ Done! Now:" -ForegroundColor Green
Write-Host "  1. Close Android Studio completely" -ForegroundColor White
Write-Host "  2. Reopen Android Studio" -ForegroundColor White
Write-Host "  3. File → Sync Project with Gradle Files" -ForegroundColor White

