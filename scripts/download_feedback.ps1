# Pulls every misclassification feedback row from the production GCS bucket
# into a local folder so you can grep/analyze them.
#
# Usage:
#   ./scripts/download_feedback.ps1
#
# Output:
#   ./feedback_corpus/misclassification/<ts>_<id>.json   (one row each)
#   ./feedback_corpus/feedback.jsonl                     (concatenated)
#
# Requires: gsutil (Google Cloud SDK), authenticated as someone who can read
#           the bucket. Run `gcloud auth login` first if needed.

$ErrorActionPreference = "Stop"

$Bucket = $env:FEEDBACK_GCS_BUCKET
if (-not $Bucket) { $Bucket = "sms-classifier-feedback" }
$Prefix = "misclassification"
$OutDir = Join-Path -Path (Get-Location) -ChildPath "feedback_corpus"

if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

Write-Host "Syncing gs://$Bucket/$Prefix -> $OutDir/..."
gsutil -m rsync -r "gs://$Bucket/$Prefix" (Join-Path $OutDir $Prefix)

# Concatenate everything into one JSONL for easy analysis.
$AllJson = Join-Path $OutDir "feedback.jsonl"
if (Test-Path $AllJson) { Remove-Item $AllJson }
Get-ChildItem -Path (Join-Path $OutDir $Prefix) -Filter "*.json" -Recurse |
    Sort-Object Name |
    ForEach-Object {
        $line = Get-Content $_.FullName -Raw
        Add-Content -Path $AllJson -Value $line.TrimEnd("`r", "`n")
    }

$count = (Get-Content $AllJson -ErrorAction SilentlyContinue | Measure-Object -Line).Lines
Write-Host "Wrote $count rows to $AllJson"
