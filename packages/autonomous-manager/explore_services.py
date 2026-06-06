#!/usr/bin/env python3
"""Explore Sapphire Services"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

print("Connecting to rari2...")
ssh.connect('100.87.225.89', username='rari', password='root', timeout=15, look_for_keys=False)

print("\n=== ALPHA ENGINE ===")
stdin, stdout, stderr = ssh.exec_command('ls -la ~/Sapphire/services/alpha-engine/ && echo "---" && cat ~/Sapphire/services/alpha-engine/main.py 2>/dev/null | head -50')
print(stdout.read().decode(errors='ignore'))

print("\n=== BOT ASTER ===")
stdin, stdout, stderr = ssh.exec_command('ls -la ~/Sapphire/services/bot-aster/')
print(stdout.read().decode(errors='ignore'))

print("\n=== BOT LIGHTER ===")
stdin, stdout, stderr = ssh.exec_command('ls -la ~/Sapphire/services/bot-lighter/')
print(stdout.read().decode(errors='ignore'))

print("\n=== MARKET SCANNER ===")
stdin, stdout, stderr = ssh.exec_command('ls -la ~/Sapphire/services/market-scanner/')
print(stdout.read().decode(errors='ignore'))

print("\n=== API GATEWAY ===")
stdin, stdout, stderr = ssh.exec_command('ls -la ~/Sapphire/services/api-gateway/')
print(stdout.read().decode(errors='ignore'))

print("\n=== WORKBENCH ===")
stdin, stdout, stderr = ssh.exec_command('ls -la ~/Sapphire/services/workbench/')
print(stdout.read().decode(errors='ignore'))

print("\n=== PINE v3 ULTRA ===")
stdin, stdout, stderr = ssh.exec_command('cat ~/Sapphire/pine/v3_ultra/*.pine 2>/dev/null | head -100 || ls ~/Sapphire/pine/v3_ultra/')
print(stdout.read().decode(errors='ignore'))

print("\n=== TRADINGVIEW WORKBENCH DOC ===")
stdin, stdout, stderr = ssh.exec_command('cat ~/Sapphire/docs/TRADINGVIEW_QUANT_WORKBENCH.md 2>/dev/null | head -150')
print(stdout.read().decode(errors='ignore'))

ssh.close()
print("\nDone!")
