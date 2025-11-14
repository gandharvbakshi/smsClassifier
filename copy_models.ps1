# PowerShell script to copy ONNX models to Android assets folder

$SourceDir = "..\android_model_exports"
$TargetDir = "app\src\main\assets"

New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null

Write-Host "Copying ONNX models..."

Copy-Item "$SourceDir\model_phishing.onnx" -Destination "$TargetDir\" -ErrorAction SilentlyContinue
Copy-Item "$SourceDir\model_isotp.onnx" -Destination "$TargetDir\" -ErrorAction SilentlyContinue
Copy-Item "$SourceDir\model_intent.onnx" -Destination "$TargetDir\" -ErrorAction SilentlyContinue

Write-Host "Copying metadata..."
Copy-Item "$SourceDir\model_metadata.json" -Destination "$TargetDir\" -ErrorAction SilentlyContinue

Write-Host "Done! Models copied to $TargetDir"

