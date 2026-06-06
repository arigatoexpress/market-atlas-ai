#!/usr/bin/env python3
"""
Deploy TradingView Desktop Autonomous Manager to Raspberry Pi mesh
"""

import paramiko
import os
import sys
from pathlib import Path
import argparse

TAILSCALE_HOSTS = {
    'rari1': '100.120.191.1',
    'rari2': '100.87.225.89'
}

DEPLOY_PATH = '/home/rari/tv-autonomous-manager'
SERVICE_NAME = 'tv-manager'


def create_remote_directory(ssh, path):
    """Create directory on remote host"""
    stdin, stdout, stderr = ssh.exec_command(f'mkdir -p {path}')
    stdout.channel.recv_exit_status()


def upload_directory(sftp, local_path, remote_path):
    """Upload directory recursively"""
    create_remote_directory(sftp.ssh, remote_path)
    
    for item in Path(local_path).rglob('*'):
        if item.is_file():
            relative_path = item.relative_to(local_path)
            remote_file_path = f"{remote_path}/{relative_path}"
            remote_dir = str(Path(remote_file_path).parent).replace('\\', '/')
            
            create_remote_directory(sftp.ssh, remote_dir)
            sftp.put(str(item), remote_file_path)
            print(f"  Uploaded: {relative_path}")


def create_systemd_service(ssh, deploy_path):
    """Create systemd service file"""
    service_content = f'''[Unit]
Description=TradingView Desktop Autonomous Manager
After=network.target

[Service]
Type=simple
User=rari
WorkingDirectory={deploy_path}/backend
Environment=PATH={deploy_path}/backend/venv/bin
Environment=PYTHONPATH={deploy_path}/backend
Environment=SAPPHIRE_WEBHOOK_URL=http://localhost:8080/tradingview/webhook
Environment=TV_HEADLESS=true
ExecStart={deploy_path}/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8081
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
'''
    
    # Write service file
    stdin, stdout, stderr = ssh.exec_command(
        f'echo "{service_content}" | sudo tee /etc/systemd/system/{SERVICE_NAME}.service'
    )
    stdout.channel.recv_exit_status()
    
    # Reload and enable
    ssh.exec_command('sudo systemctl daemon-reload')
    ssh.exec_command(f'sudo systemctl enable {SERVICE_NAME}')


def deploy_to_host(hostname, ip, username='rari', password='root'):
    """Deploy to a single host"""
    print(f"\n{'='*60}")
    print(f"Deploying to {hostname} ({ip})")
    print(f"{'='*60}")
    
    try:
        # Connect
        print(f"Connecting to {hostname}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password, timeout=15)
        
        # Create deploy directory
        print(f"Creating directory structure...")
        create_remote_directory(ssh, DEPLOY_PATH)
        
        # Upload files
        print(f"Uploading files...")
        sftp = ssh.open_sftp()
        upload_directory(sftp, 'backend', f'{DEPLOY_PATH}/backend')
        upload_directory(sftp, 'config', f'{DEPLOY_PATH}/config')
        sftp.close()
        
        # Setup Python environment
        print(f"Setting up Python environment...")
        commands = [
            f'cd {DEPLOY_PATH}/backend',
            'python3 -m venv venv',
            'venv/bin/pip install --upgrade pip',
            'venv/bin/pip install -r requirements.txt',
            'venv/bin/playwright install chromium'
        ]
        
        for cmd in commands:
            print(f"  Running: {cmd}")
            stdin, stdout, stderr = ssh.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                error = stderr.read().decode()
                print(f"  Error: {error}")
        
        # Create systemd service
        print(f"Creating systemd service...")
        create_systemd_service(ssh, DEPLOY_PATH)
        
        # Start service
        print(f"Starting service...")
        ssh.exec_command(f'sudo systemctl restart {SERVICE_NAME}')
        
        # Check status
        stdin, stdout, stderr = ssh.exec_command(f'systemctl is-active {SERVICE_NAME}')
        status = stdout.read().decode().strip()
        print(f"Service status: {status}")
        
        ssh.close()
        print(f"\nDeployment to {hostname} completed!")
        return True
        
    except Exception as e:
        print(f"Error deploying to {hostname}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Deploy TV Manager to Pi mesh')
    parser.add_argument('--host', choices=['rari1', 'rari2', 'all'], default='all',
                       help='Target host')
    parser.add_argument('--username', default='rari', help='SSH username')
    parser.add_argument('--password', default='root', help='SSH password')
    
    args = parser.parse_args()
    
    # Determine targets
    if args.host == 'all':
        targets = TAILSCALE_HOSTS.items()
    else:
        targets = [(args.host, TAILSCALE_HOSTS[args.host])]
    
    # Deploy to each target
    results = {}
    for hostname, ip in targets:
        success = deploy_to_host(hostname, ip, args.username, args.password)
        results[hostname] = success
    
    # Summary
    print(f"\n{'='*60}")
    print("DEPLOYMENT SUMMARY")
    print(f"{'='*60}")
    for hostname, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {hostname}: {status}")
    
    # Return exit code
    return 0 if all(results.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
