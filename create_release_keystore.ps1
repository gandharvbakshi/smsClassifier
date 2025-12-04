# Create a release keystore for Google Play Store
# IMPORTANT: Keep this keystore safe! You'll need it for all future updates.

$keystorePath = "$PSScriptRoot\release-keystore.jks"
$keystorePassword = Read-Host "Enter keystore password (min 6 chars, remember this!)" -AsSecureString
$keyAlias = Read-Host "Enter key alias (default: release-key)" 
if ([string]::IsNullOrWhiteSpace($keyAlias)) {
    $keyAlias = "release-key"
}
$keyPassword = Read-Host "Enter key password (can be same as keystore)" -AsSecureString

# Convert secure strings to plain text (needed for keytool)
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($keystorePassword)
$keystorePasswordPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($keyPassword)
$keyPasswordPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

Write-Host "`nCreating release keystore..." -ForegroundColor Cyan

# Check if keytool is available
$keytoolPath = "$env:JAVA_HOME\bin\keytool.exe"
if (-not (Test-Path $keytoolPath)) {
    # Try common locations or use system PATH
    $keytoolPath = "keytool"
}

# Get user details for certificate
$cn = Read-Host "Enter your name or organization name"
$ou = Read-Host "Enter organizational unit (optional)"
$o = Read-Host "Enter organization (optional)"
$l = Read-Host "Enter city/location (optional)"
$st = Read-Host "Enter state/province (optional)"
$c = Read-Host "Enter country code (2 letters, e.g., US, IN)"

$dname = "CN=$cn"
if ($ou) { $dname += ", OU=$ou" }
if ($o) { $dname += ", O=$o" }
if ($l) { $dname += ", L=$l" }
if ($st) { $dname += ", ST=$st" }
if ($c) { $dname += ", C=$c" }

# Create keystore
& $keytoolPath -genkey -v `
    -keystore $keystorePath `
    -alias $keyAlias `
    -keyalg RSA `
    -keysize 2048 `
    -validity 25000 `
    -storepass $keystorePasswordPlain `
    -keypass $keyPasswordPlain `
    -dname $dname

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[SUCCESS] Release keystore created successfully!" -ForegroundColor Green
    Write-Host "`n[WARNING] CRITICAL: Save these details securely!" -ForegroundColor Red
    Write-Host "`nKeystore details:" -ForegroundColor Yellow
    Write-Host "  Path: $keystorePath"
    Write-Host "  Alias: $keyAlias"
    Write-Host "  Store Password: [YOUR PASSWORD]"
    Write-Host "  Key Password: [YOUR PASSWORD]"
    Write-Host '  Validity: 25 years (25000 days)'
    Write-Host "`nNext steps:" -ForegroundColor Cyan
    Write-Host "  1. Save the keystore file in a secure location (backup!)"
    Write-Host "  2. Create keystore.properties file (see GOOGLE_PLAY_DEPLOYMENT_PLAN.md)"
    Write-Host "  3. Add keystore.properties to .gitignore"
    Write-Host "  4. Build release AAB for Google Play"
} else {
    Write-Host "`n[ERROR] Failed to create keystore. Make sure Java is installed." -ForegroundColor Red
    Write-Host "  JAVA_HOME should point to your JDK installation." -ForegroundColor Yellow
}

