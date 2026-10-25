param(
    [Parameter(Mandatory=$true)][string]$StudentId,
    [Parameter(Mandatory=$true)][string]$StudentName,
    [string]$Destination = "$env:USERPROFILE\Desktop",
    [string]$VideoPath = "",
    [string]$VideoName = ""
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$stage = Join-Path $tempRoot ("Homework2_Submission_" + [guid]::NewGuid().ToString("N"))

New-Item -ItemType Directory -Path $stage | Out-Null

$items = @(
    "main.py",
    "README.md",
    "Design.md",
    "requirements.txt",
    "run_deepseek.ps1",
    "run_deepseek.bat",
    "run_mock.ps1",
    ".env.example",
    ".gitignore",
    "workflow",
    "sample_project",
    "output"
)

foreach ($item in $items) {
    $source = Join-Path $root $item
    if (Test-Path -LiteralPath $source) {
        Copy-Item -LiteralPath $source -Destination $stage -Recurse -Force
    }
}

# 明确排除依赖、缓存和本地密钥
$excludeDirs = @(".venv", ".idea", "__pycache__", ".pytest_cache")
Get-ChildItem -LiteralPath $stage -Recurse -Directory -Force |
    Where-Object { $excludeDirs -contains $_.Name } |
    Remove-Item -Recurse -Force
Get-ChildItem -LiteralPath $stage -Recurse -File -Force -Filter "*.pyc" | Remove-Item -Force

if ($VideoPath -and (Test-Path -LiteralPath $VideoPath)) {
    if ($VideoName) {
        Copy-Item -LiteralPath $VideoPath -Destination (Join-Path $stage $VideoName) -Force
    } else {
        Copy-Item -LiteralPath $VideoPath -Destination $stage -Force
    }
}

$sizeBytes = (Get-ChildItem -LiteralPath $stage -Recurse -File | Measure-Object Length -Sum).Sum
$sizeMB = [math]::Round($sizeBytes / 1MB, 2)
if ($sizeMB -ge 200) {
    throw "Package content is $sizeMB MB, which exceeds the 200 MB requirement."
}

$zipPath = Join-Path $Destination ("$StudentId-$StudentName.zip")
if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zipPath -CompressionLevel Optimal

$resolvedStage = (Resolve-Path -LiteralPath $stage).Path
if (-not $resolvedStage.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to remove unexpected staging path: $resolvedStage"
}
Remove-Item -LiteralPath $resolvedStage -Recurse -Force

Write-Output "ZIP: $zipPath"
Write-Output "CONTENT_SIZE_MB: $sizeMB"
