# DeepSeek 一键运行（读取项目根目录 .env）
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python main.py --type all --output-dir output
