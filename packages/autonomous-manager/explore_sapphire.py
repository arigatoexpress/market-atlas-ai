#!/usr/bin/env python3
"""Explore Sapphire Trading System Architecture"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

print("Connecting to rari2 Sapphire system...")
ssh.connect('100.87.225.89', username='rari', password='root', timeout=15, look_for_keys=False)

print("\n=== SAPPHIRE SERVICES ===")
stdin, stdout, stderr = ssh.exec_command('ls -la ~/Sapphire/services/')
print(stdout.read().decode())

print("\n=== SAPPHIRE PINE SCRIPTS ===")
stdin, stdout, stderr = ssh.exec_command('ls -la ~/Sapphire/pine/')
print(stdout.read().decode())

print("\n=== README ===")
stdin, stdout, stderr = ssh.exec_command('head -100 ~/Sapphire/README.md')
print(stdout.read().decode())

print("\n=== HANDOFF ===")
stdin, stdout, stderr = ssh.exec_command('head -100 ~/Sapphire/HANDOFF.md')
print(stdout.read().decode())

print("\n=== INFRASTRUCTURE STATUS ===")
stdin, stdout, stderr = ssh.exec_command('cat ~/Sapphire/INFRASTRUCTURE_STATUS.md')
print(stdout.read().decode())

print("\n=== RUNNING PROCESSES ===")
stdin, stdout, stderr = ssh.exec_command('ps aux | grep -E "(sapphire|trading|python)" | grep -v grep')
print(stdout.read().decode())

print("\n=== DOCKER STATUS ===")
stdin, stdout, stderr = ssh.exec_command('docker ps 2>/dev/null || echo "Docker not running"')
print(stdout.read().decode())

print("\n=== TRADING LOGS ===")
stdin, stdout, stderr = ssh.exec_command('ls -la ~/trading-logs/ 2>/dev/null || echo "No trading-logs"')
print(stdout.read().decode())

ssh.close()
print("\nDone!")
