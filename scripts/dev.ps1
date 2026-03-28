# Script khởi chạy bộ đôi: App Server + Cloudflare Tunnel
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Đảm bảo chạy từ thư mục gốc của project
$rootDir = (Get-Item $PSScriptRoot).Parent.FullName
Set-Location -Path $rootDir

$envFile = Join-Path $rootDir ".env"
$token = ""

if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $trimmed = $_.Trim()
        if ($trimmed -and -not $trimmed.StartsWith("#")) {
            $name, $value = $trimmed -split "=", 2
            if ($name -eq "CLOUDFLARE_TUNNEL_TOKEN") { $token = $value }
        }
    }
}

# 1. Khởi chạy Tunnel trong background (nếu có token)
if ($token -and $token -ne "your_token_here") {
    Write-Host "--- Khởi động Cloudflare Tunnel (Background) ---" -ForegroundColor Cyan
    $tunnelJob = Start-Job -ScriptBlock { 
        param($t) cloudflared tunnel run --token $t 
    } -ArgumentList $token
} else {
    Write-Host "--- Bỏ qua Tunnel (Chưa cấu hình token trong .env) ---" -ForegroundColor Yellow
}

# 2. Khởi chạy Uvicorn Server (Foreground)
Write-Host "--- Khởi động Uvicorn Server (Port 8003) ---" -ForegroundColor Green
try {
    .\venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8003 --reload
}
finally {
    # 3. Dọn dẹp: Dừng tunnel khi tắt server
    if ($tunnelJob) {
        Write-Host "`n--- Đang dừng Cloudflare Tunnel... ---" -ForegroundColor Gray
        Stop-Job $tunnelJob
        Remove-Job $tunnelJob
    }
}
