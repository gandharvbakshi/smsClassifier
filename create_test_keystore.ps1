# Create a test keystore for signing release APKs
# This is for testing only - NOT for Google Play Store

$keystorePath = "$PSScriptRoot\test-keystore.jks"
$keystorePassword = "test123456"
$keyAlias = "test-key"
$keyPassword = "test123456"

Write-Host "Creating test keystore at: $keystorePath" -ForegroundColor Cyan

# Check if keytool is available
$keytoolPath = "$env:JAVA_HOME\bin\keytool.exe"
if (-not (Test-Path $keytoolPath)) {
    # Try common locations
    $keytoolPath = "keytool"
}

# Create keystore
& $keytoolPath -genkey -v `
    -keystore $keystorePath `
    -alias $keyAlias `
    -keyalg RSA `
    -keysize 2048 `
    -validity 10000 `
    -storepass $keystorePassword `
    -keypass $keyPassword `
    -dname "CN=Test, OU=Test, O=Test, L=Test, ST=Test, C=US"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✓ Test keystore created successfully!" -ForegroundColor Green
    Write-Host "`nKeystore details:" -ForegroundColor Yellow
    Write-Host "  Path: $keystorePath"
    Write-Host "  Alias: $keyAlias"
    Write-Host "  Store Password: $keystorePassword"
    Write-Host "  Key Password: $keyPassword"
    Write-Host "`n⚠️  IMPORTANT: This is for TESTING ONLY!" -ForegroundColor Red
    Write-Host "   For Google Play, you'll need to create a proper release keystore." -ForegroundColor Yellow
} else {
    Write-Host "`n✗ Failed to create keystore. Make sure Java is installed." -ForegroundColor Red
}

