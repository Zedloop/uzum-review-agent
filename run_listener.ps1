$scriptDir = "c:\Users\VICTUS\Desktop\uzum-review-agent\uzum-review-agent"
$env:PYTHONUTF8 = "1"
$env:PYTHONUNBUFFERED = "1"

Set-Location $scriptDir
New-Item -ItemType Directory -Force -Path "$scriptDir\data" | Out-Null

& "$scriptDir\venv\Scripts\python.exe" -u bot_listener.py *>> "$scriptDir\data\listener_log.txt"
