#!/usr/bin/env powershell
<#
.SYNOPSIS
    Launch TradingView Desktop with CDP (Chrome DevTools Protocol) for Autonomous Control
.DESCRIPTION
    Closes any running TradingView instances and relaunches with remote debugging enabled
#>

$TVPath = "$env:USERPROFILE\AppData\Local\Programs\TradingView\TradingView.exe"
$CDPPort = 9222

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  TradingView Desktop - CDP Launcher" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# Check if TV is installed
if (-not (Test-Path $TVPath)) {
    Write-Host "ERROR: TradingView Desktop not found at:" -ForegroundColor Red
    Write-Host "  $TVPath" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please install TradingView Desktop from:" -ForegroundColor Yellow
    Write-Host "  https://www.tradingview.com/desktop/" -ForegroundColor Cyan
    exit 1
}

Write-Host "Found TradingView Desktop at:" -ForegroundColor Green
Write-Host "  $TVPath" -ForegroundColor Gray
Write-Host ""

# Check if already running
$tvProcess = Get-Process -Name "TradingView" -ErrorAction SilentlyContinue
if ($tvProcess) {
    Write-Host "TradingView Desktop is currently running." -ForegroundColor Yellow
    Write-Host "Closing it to restart with CDP port..." -ForegroundColor Yellow
    
    # Try graceful close first
    $tvProcess | ForEach-Object { $_.CloseMainWindow() | Out-Null }
    Start-Sleep -Seconds 2
    
    # Force kill if still running
    $tvProcess = Get-Process -Name "TradingView" -ErrorAction SilentlyContinue
    if ($tvProcess) {
        $tvProcess | Stop-Process -Force
        Write-Host "Force closed TradingView Desktop" -ForegroundColor Yellow
    }
    
    Start-Sleep -Seconds 1
}

# Check if port is already in use
$portInUse = Get-NetTCPConnection -LocalPort $CDPPort -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "WARNING: Port $CDPPort is already in use!" -ForegroundColor Red
    Write-Host "Process using port: $($portInUse.OwningProcess)" -ForegroundColor Yellow
    Write-Host ""
}

# Launch TradingView with CDP
Write-Host "Launching TradingView Desktop with CDP port $CDPPort..." -ForegroundColor Green
Write-Host ""

try {
    Start-Process -FilePath $TVPath -ArgumentList "--remote-debugging-port=$CDPPort" -WindowStyle Normal
    
    Write-Host "TradingView Desktop launched successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Waiting for initialization..." -ForegroundColor Gray
    
    # Wait for TV to fully load
    for ($i = 10; $i -gt 0; $i--) {
        Write-Host "  $i seconds remaining..." -ForegroundColor Gray -NoNewline
        Start-Sleep -Seconds 1
        Write-Host "`r                                  `r" -NoNewline
    }
    
    Write-Host "TradingView Desktop should now be ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Wait for TradingView to fully load" -ForegroundColor White
    Write-Host "  2. Open a chart if not already open" -ForegroundColor White
    Write-Host "  3. Connect via API:" -ForegroundColor White
    Write-Host "     curl -X POST http://100.71.10.48:8081/tv/connect" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Or run the connect script:" -ForegroundColor Cyan
    Write-Host "  .\connect_and_test.ps1" -ForegroundColor Yellow
    
} catch {
    Write-Host "ERROR: Failed to launch TradingView Desktop" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
