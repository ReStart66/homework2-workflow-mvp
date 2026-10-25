# 一键运行 Mock 演示（无需 API Key）
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python main.py --repo sample_project --type all --mock --output-dir output
