#!/usr/bin/env powershell
<#
.SYNOPSIS
    Connect to TradingView Desktop and run autonomous control tests
.DESCRIPTION
    Connects to TradingView via API and tests all autonomous control features
#>

$APIBase = "http://localhost:8081"

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  TradingView Autonomous Control - Test" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

function Test-API {
    param($Method, $Endpoint, $Body = $null)
    
    try {
        $uri = "$APIBase$Endpoint"
        if ($Method -eq "GET") {
            $response = Invoke-RestMethod -Uri $uri -Method GET -TimeoutSec 10
        } else {
            if ($Body) {
                $jsonBody = $Body | ConvertTo-Json -Depth 10
                $response = Invoke-RestMethod -Uri $uri -Method POST -Body $jsonBody -ContentType "application/json" -TimeoutSec 10
            } else {
                $response = Invoke-RestMethod -Uri $uri -Method POST -TimeoutSec 30
            }
        }
        return $response
    } catch {
        return @{ error = $_.Exception.Message }
    }
}

# Step 1: Check if TV is running with CDP
Write-Host "Step 1: Checking TradingView Desktop..." -ForegroundColor Gray
$cdpCheck = Test-NetConnection -ComputerName localhost -Port 9222 -WarningAction SilentlyContinue
if ($cdpCheck.TcpTestSucceeded) {
    Write-Host "  [OK] TradingView Desktop is listening on port 9222" -ForegroundColor Green
} else {
    Write-Host "  [WARN] TradingView Desktop not detected on port 9222" -ForegroundColor Yellow
    Write-Host "  Make sure TV is running with: --remote-debugging-port=9222" -ForegroundColor Yellow
}
Write-Host ""

# Step 2: Connect to TradingView
Write-Host "Step 2: Connecting to TradingView Desktop..." -ForegroundColor Gray
Write-Host "  (This may take 10-15 seconds...)" -ForegroundColor Gray

$connectResult = Test-API -Method "POST" -Endpoint "/tv/connect"

if ($connectResult.error) {
    Write-Host "  [FAIL] Connection failed: $($connectResult.error)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Ensure TradingView Desktop is running" -ForegroundColor White
    Write-Host "  2. Check it's launched with: --remote-debugging-port=9222" -ForegroundColor White
    Write-Host "  3. Try running: .\launch_tv_with_cdp.ps1" -ForegroundColor White
    exit 1
}

Write-Host "  [OK] Connected to TradingView Desktop!" -ForegroundColor Green
Write-Host "  Status: $($connectResult.status)" -ForegroundColor Gray
Write-Host "  Message: $($connectResult.message)" -ForegroundColor Gray
if ($connectResult.config) {
    Write-Host "  Config: headless=$($connectResult.config.headless), port=$($connectResult.config.cdp_port)" -ForegroundColor Gray
}
Write-Host ""
Start-Sleep -Seconds 2

# Step 3: Get current state
Write-Host "Step 3: Getting current chart state..." -ForegroundColor Gray
$stateResult = Test-API -Method "GET" -Endpoint "/tv/state"

if ($stateResult.error) {
    Write-Host "  [WARN] Could not get state: $($stateResult.error)" -ForegroundColor Yellow
} else {
    Write-Host "  [OK] Chart State:" -ForegroundColor Green
    Write-Host "    Symbol: $($stateResult.symbol)" -ForegroundColor White
    Write-Host "    Timeframe: $($stateResult.timeframe)" -ForegroundColor White
    Write-Host "    Price: $($stateResult.current_price)" -ForegroundColor White
    Write-Host "    Indicators: $($stateResult.active_indicators -join ', ')" -ForegroundColor White
    Write-Host "    Chart Loaded: $($stateResult.is_chart_loaded)" -ForegroundColor White
}
Write-Host ""
Start-Sleep -Seconds 1

# Step 4: Test symbol changes
Write-Host "Step 4: Testing symbol changes..." -ForegroundColor Gray
$symbols = @("BTCUSDT", "ETHUSDT", "SOLUSDT")

foreach ($symbol in $symbols) {
    Write-Host "  Changing to $symbol..." -ForegroundColor Gray -NoNewline
    $result = Test-API -Method "POST" -Endpoint "/tv/symbol/$symbol"
    if ($result.error) {
        Write-Host " [FAIL]" -ForegroundColor Red
    } else {
        Write-Host " [OK]" -ForegroundColor Green
    }
    Start-Sleep -Seconds 1
}
Write-Host ""

# Step 5: Test timeframe changes
Write-Host "Step 5: Testing timeframe changes..." -ForegroundColor Gray
$timeframes = @("1h", "4h", "1d")

foreach ($tf in $timeframes) {
    Write-Host "  Changing to $tf..." -ForegroundColor Gray -NoNewline
    $result = Test-API -Method "POST" -Endpoint "/tv/timeframe/$tf"
    if ($result.error) {
        Write-Host " [FAIL]" -ForegroundColor Red
    } else {
        Write-Host " [OK]" -ForegroundColor Green
    }
    Start-Sleep -Seconds 1
}
Write-Host ""

# Step 6: Test adding indicators
Write-Host "Step 6: Testing indicator addition..." -ForegroundColor Gray
$indicators = @("RSI", "MACD")

foreach ($ind in $indicators) {
    Write-Host "  Adding $ind..." -ForegroundColor Gray -NoNewline
    $result = Test-API -Method "POST" -Endpoint "/tv/indicator/$ind"
    if ($result.error) {
        Write-Host " [FAIL]" -ForegroundColor Red
    } else {
        Write-Host " [OK]" -ForegroundColor Green
    }
    Start-Sleep -Seconds 2
}
Write-Host ""

# Step 7: Take screenshot
Write-Host "Step 7: Capturing screenshot..." -ForegroundColor Gray
$screenshotResult = Test-API -Method "POST" -Endpoint "/tv/screenshot"

if ($screenshotResult.error) {
    Write-Host "  [FAIL] Screenshot failed: $($screenshotResult.error)" -ForegroundColor Red
} else {
    $screenshotData = $screenshotResult.screenshot
    if ($screenshotData) {
        Write-Host "  [OK] Screenshot captured!" -ForegroundColor Green
        Write-Host "    Size: $($screenshotData.Length) characters (base64)" -ForegroundColor Gray
        
        # Save screenshot to file
        $screenshotPath = "$PSScriptRoot\screenshot_$(Get-Date -Format 'yyyyMMdd_HHmmss').png"
        try {
            $bytes = [Convert]::FromBase64String($screenshotData)
            [IO.File]::WriteAllBytes($screenshotPath, $bytes)
            Write-Host "    Saved to: $screenshotPath" -ForegroundColor Green
        } catch {
            Write-Host "    Could not save screenshot: $_" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  [WARN] No screenshot data returned" -ForegroundColor Yellow
    }
}
Write-Host ""

# Step 8: Final state
Write-Host "Step 8: Getting final state..." -ForegroundColor Gray
$finalState = Test-API -Method "GET" -Endpoint "/tv/state"

if ($finalState.error) {
    Write-Host "  [WARN] Could not get final state" -ForegroundColor Yellow
} else {
    Write-Host "  [OK] Final Chart State:" -ForegroundColor Green
    Write-Host "    Symbol: $($finalState.symbol)" -ForegroundColor White
    Write-Host "    Timeframe: $($finalState.timeframe)" -ForegroundColor White
    Write-Host "    Indicators: $($finalState.active_indicators -join ', ')" -ForegroundColor White
}
Write-Host ""

# Summary
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  AUTONOMOUS CONTROL TEST COMPLETE!" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "TradingView Desktop is now under autonomous control!" -ForegroundColor Green
Write-Host ""
Write-Host "You can control it from your Mac using:" -ForegroundColor Cyan
Write-Host "  curl http://100.71.10.48:8081/tv/state" -ForegroundColor Yellow
Write-Host "  curl -X POST http://100.71.10.48:8081/tv/symbol/BTCUSDT" -ForegroundColor Yellow
Write-Host "  curl -X POST http://100.71.10.48:8081/tv/screenshot" -ForegroundColor Yellow
