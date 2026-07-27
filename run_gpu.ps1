$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:PYTHONPATH = "$PSScriptRoot\src" + $(if ($env:PYTHONPATH) { ";$env:PYTHONPATH" } else { "" })
python -m se --config configs/mvp_100k.json --output runs/mvp_100k_gpu --backend gpu
