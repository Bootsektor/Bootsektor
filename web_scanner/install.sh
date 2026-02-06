#!/usr/bin/env python3
"""
Web Scanner Installation and Setup Script
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def check_python_version():
    """Check Python version compatibility"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    
    print(f"✅ Python version: {sys.version}")
    return True

def check_system_dependencies():
    """Check system dependencies"""
    print("🔍 Checking system dependencies...")
    
    # Check for TOR
    try:
        result = subprocess.run(['which', 'tor'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ TOR is installed")
        else:
            print("⚠️  TOR is not installed. Please install TOR for anonymous browsing:")
            print("   Ubuntu/Debian: sudo apt install tor")
            print("   CentOS/RHEL: sudo yum install tor")
            print("   Arch: sudo pacman -S tor")
    except:
        print("⚠️  Could not check TOR installation")
    
    # Check for image processing libraries
    try:
        result = subprocess.run(['which', 'convert'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ ImageMagick is installed")
        else:
            print("⚠️  ImageMagick is not installed. Please install for better image processing:")
            print("   Ubuntu/Debian: sudo apt install imagemagick")
            print("   CentOS/RHEL: sudo yum install ImageMagick")
            print("   Arch: sudo pacman -S imagemagick")
    except:
        print("⚠️  Could not check ImageMagick installation")

def create_virtual_environment():
    """Create Python virtual environment"""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("✅ Virtual environment already exists")
        return str(venv_path / "bin" / "activate")
    
    print("📦 Creating virtual environment...")
    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✅ Virtual environment created successfully")
        return str(venv_path / "bin" / "activate")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error creating virtual environment: {e}")
        return None

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")
    
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print("❌ requirements.txt not found")
        return False
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ], check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")
    
    directories = [
        "data",
        "data/images",
        "data/summaries",
        "logs",
        "config"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")

def create_default_config():
    """Create default configuration file"""
    config_file = Path("config/config.json")
    
    if config_file.exists():
        print("✅ Configuration file already exists")
        return
    
    print("⚙️  Creating default configuration...")
    
    default_config = {
        "scan_interval": 3600,
        "websites": [
            {
                "url": "https://news.ycombinator.com",
                "name": "Hacker News",
                "selectors": {
                    "articles": "tr.athing",
                    "title": "titlelink",
                    "content": "comment",
                    "image": "img",
                    "link": "a"
                },
                "enabled": True
            }
        ],
        "tor": {
            "enabled": True,
            "port": 9050,
            "control_port": 9051,
            "password": ""
        },
        "content_filter": {
            "keywords": ["python", "programming", "technology", "ai", "machine learning"],
            "blacklist": ["spam", "advertisement", "sponsored"],
            "min_content_length": 100,
            "learning_enabled": True
        },
        "image_processing": {
            "width": 800,
            "height": 600,
            "font_size": 24,
            "quality": 85
        },
        "telegram": {
            "enabled": False,
            "bot_token": "",
            "chat_id": "",
            "proxy": {
                "enabled": False,
                "url": ""
            }
        },
        "database": {
            "type": "sqlite",
            "path": "data/scanner.db"
        },
        "logging": {
            "level": "INFO",
            "max_files": 7
        }
    }
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        print("✅ Default configuration created")
        print(f"📝 Please edit {config_file} to customize your settings")
    except Exception as e:
        print(f"❌ Error creating configuration: {e}")

def create_systemd_service():
    """Create systemd service file for auto-start"""
    service_file = Path("web-scanner.service")
    
    print("🔧 Creating systemd service file...")
    
    service_content = f"""[Unit]
Description=Web Scanner Service
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'root')}
WorkingDirectory={Path.cwd()}
ExecStart={sys.executable} {Path.cwd()}/src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    try:
        with open(service_file, 'w') as f:
            f.write(service_content)
        
        print("✅ Systemd service file created")
        print("📋 To install the service, run:")
        print(f"   sudo cp {service_file} /etc/systemd/system/")
        print("   sudo systemctl daemon-reload")
        print("   sudo systemctl enable web-scanner")
        print("   sudo systemctl start web-scanner")
        
    except Exception as e:
        print(f"❌ Error creating service file: {e}")

def create_startup_scripts():
    """Create startup and management scripts"""
    print("📜 Creating startup scripts...")
    
    # Start script
    start_script = Path("start.sh")
    start_content = f"""#!/bin/bash
echo "🚀 Starting Web Scanner..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run install.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Start the scanner
cd {Path.cwd()}
python src/main.py
"""
    
    # Stop script
    stop_script = Path("stop.sh")
    stop_content = """#!/bin/bash
echo "🛑 Stopping Web Scanner..."

# Kill any running scanner processes
pkill -f "python src/main.py"

echo "✅ Web Scanner stopped"
"""
    
    # Status script
    status_script = Path("status.sh")
    status_content = """#!/bin/bash
echo "📊 Web Scanner Status"

# Check if scanner is running
if pgrep -f "python src/main.py" > /dev/null; then
    echo "✅ Scanner is running"
    echo "📋 Process info:"
    ps aux | grep "python src/main.py" | grep -v grep
else
    echo "❌ Scanner is not running"
fi
"""
    
    try:
        # Write scripts
        with open(start_script, 'w') as f:
            f.write(start_content)
        start_script.chmod(0o755)
        
        with open(stop_script, 'w') as f:
            f.write(stop_content)
        stop_script.chmod(0o755)
        
        with open(status_script, 'w') as f:
            f.write(status_content)
        status_script.chmod(0o755)
        
        print("✅ Startup scripts created:")
        print("   ./start.sh - Start the scanner")
        print("   ./stop.sh - Stop the scanner")
        print("   ./status.sh - Check status")
        
    except Exception as e:
        print(f"❌ Error creating startup scripts: {e}")

def print_next_steps():
    """Print next steps for the user"""
    print("\n🎉 Installation completed successfully!")
    print("\n📋 Next steps:")
    print("1. Edit config/config.json to add your websites and settings")
    print("2. Set up Telegram bot if you want notifications (optional)")
    print("3. Start TOR service: sudo systemctl start tor")
    print("4. Run the scanner: ./start.sh")
    print("5. Check status: ./status.sh")
    
    print("\n📖 For more information, see README.md")

def main():
    """Main installation function"""
    print("🔧 Web Scanner Installation Script")
    print("=" * 40)
    
    # Change to web_scanner directory
    scanner_dir = Path("web_scanner")
    if scanner_dir.exists():
        os.chdir(scanner_dir)
        print(f"📁 Changed to directory: {scanner_dir}")
    
    # Run installation steps
    if not check_python_version():
        return False
    
    check_system_dependencies()
    create_directories()
    create_default_config()
    
    # Install Python dependencies
    if not install_dependencies():
        print("⚠️  Continuing with installation despite dependency issues...")
    
    create_startup_scripts()
    create_systemd_service()
    
    print_next_steps()
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Installation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Installation failed: {e}")
        sys.exit(1)