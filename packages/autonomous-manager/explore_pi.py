#!/usr/bin/env python3
"""Explore Raspberry Pi trading system"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

print("Connecting to rari2...")
ssh.connect('100.87.225.89', username='rari', password='root', timeout=15, look_for_keys=False)

# Explore Sapphire directory
print("\n=== SAPPHIRE DIRECTORY ===")
stdin, stdout, stderr = ssh.exec_command('ls -la ~/Sapphire')
print(stdout.read().decode())

print("\n=== SAPPHIRE TRADING CONFIG ===")
stdin, stdout, stderr = ssh.exec_command('ls -la ~/.sapphire_trading 2>/dev/null || echo "Not found"')
print(stdout.read().decode())

print("\n=== TRADING MONITOR ===")
stdin, stdout, stderr = ssh.exec_command('ls -la ~/sapphire_trading_monitor 2>/dev/null || echo "Not found"')
print(stdout.read().decode())

print("\n=== KIMI BOT ===")
stdin, stdout, stderr = ssh.exec_command('ls -la ~/kimi-bot 2>/dev/null || echo "Not found"')
print(stdout.read().decode())

print("\n=== KIMI CLAW ===")
stdin, stdout, stderr = ssh.exec_command('ls -la ~/kimi-claw 2>/dev/null || echo "Not found"')
print(stdout.read().decode())

print("\n=== BOT LOG (last 50 lines) ===")
stdin, stdout, stderr = ssh.exec_command('tail -50 ~/bot.log 2>/dev/null || echo "No bot.log"')
print(stdout.read().decode())

print("\n=== LIGHTER ENV ===")
stdin, stdout, stderr = ssh.exec_command('cat ~/lighter.env 2>/dev/null || echo "No lighter.env"')
print(stdout.read().decode())

print("\n=== SAPPHIRE ALERT STATE ===")
stdin, stdout, stderr = ssh.exec_command('cat ~/.sapphire_alert_state.json 2>/dev/null || echo "No alert state"')
print(stdout.read().decode())

ssh.close()
print("\nDone!")
