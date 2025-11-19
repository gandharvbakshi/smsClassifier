# Verify Android Emulator Network Connectivity
# Run this script after starting the emulator

Write-Host "Checking emulator network connectivity..." -ForegroundColor Cyan

# Check if emulator is connected
$devices = adb devices
if ($devices -notmatch "emulator") {
    Write-Host "ERROR: No emulator detected. Please start the emulator first." -ForegroundColor Red
    exit 1
}

Write-Host "`n1. Testing basic connectivity (ping Google DNS)..." -ForegroundColor Yellow
adb shell "ping -c 3 8.8.8.8"
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Basic connectivity OK" -ForegroundColor Green
} else {
    Write-Host "✗ Basic connectivity FAILED" -ForegroundColor Red
    Write-Host "  The emulator cannot reach the internet." -ForegroundColor Red
    Write-Host "  Try: Cold Boot the emulator (Device Manager → ▼ → Cold Boot Now)" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n2. Testing DNS resolution..." -ForegroundColor Yellow
$dnsResult = adb shell "nslookup sms-ensemble-hhpimusmbq-el.a.run.app 2>&1"
if ($dnsResult -match "Address") {
    Write-Host "✓ DNS resolution OK" -ForegroundColor Green
    Write-Host $dnsResult
} else {
    Write-Host "✗ DNS resolution FAILED" -ForegroundColor Red
    Write-Host $dnsResult
    Write-Host "`nTrying to fix DNS..." -ForegroundColor Yellow
    adb shell "settings put global private_dns_mode off"
    Write-Host "  Restart the app and try again." -ForegroundColor Yellow
}

Write-Host "`n=== Summary ===" -ForegroundColor Cyan
Write-Host "If all tests pass, the app should be able to connect to Cloud Run." -ForegroundColor Green
Write-Host "If tests fail, try:" -ForegroundColor Yellow
Write-Host "  1. Cold Boot the emulator" -ForegroundColor Yellow
Write-Host "  2. Check your host machine's internet connection" -ForegroundColor Yellow
Write-Host "  3. Use a physical device instead" -ForegroundColor Yellow

