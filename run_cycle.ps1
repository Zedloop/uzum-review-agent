$scriptDir = "c:\Users\VICTUS\Desktop\uzum-review-agent\uzum-review-agent"
$env:PYTHONUTF8 = "1"
$env:UZUM_AGENT_LOG = "$scriptDir\data\run_log.txt"

Set-Location $scriptDir
New-Item -ItemType Directory -Force -Path "$scriptDir\data" | Out-Null

# Uyqudan uyg'ongandan keyin Wi-Fi/DNS darhol ishlamasligi mumkin,
# shuning uchun internet qaytguncha kutamiz (eng ko'pi bilan ~60 soniya).
$networkReady = $false
for ($i = 0; $i -lt 20; $i++) {
    try {
        [System.Net.Dns]::GetHostEntry("api-seller.uzum.uz") | Out-Null
        $networkReady = $true
        break
    } catch {
        Start-Sleep -Seconds 3
    }
}

if (-not $networkReady) {
    Add-Content -Path $env:UZUM_AGENT_LOG -Value "--- $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | internet 60s ichida topilmadi, o'tkazib yuborildi ---"
    exit
}

& "$scriptDir\venv\Scripts\python.exe" main.py check
& "$scriptDir\venv\Scripts\python.exe" main.py draft
