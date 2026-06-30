#!/usr/bin/env python3
"""
Setup script for endpoint configuration editor
"""

import subprocess
import sys
import os

def install_requirements():
    """Install required packages"""
    packages = [
        "rich",
        "textual",
        "click"
    ]
    
    for package in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✓ Installed {package}")
        except subprocess.CalledProcessError:
            print(f"✗ Failed to install {package}")
            return False
    
    return True

def main():
    """Main setup function"""
    print("🚀 Setting up Endpoint Configuration Editor...")
    
    if install_requirements():
        print("\n✅ Setup completed successfully!")
        print("\nUsage:")
        print("  python endpoint_editor.py           # Launch TUI mode")
        print("  python endpoint_editor.py --cli    # Launch CLI mode")
        print("\nMake the script executable:")
        print("  chmod +x endpoint_editor.py")
        print("  ./endpoint_editor.py")
    else:
        print("\n❌ Setup failed. Please install packages manually:")
        print("  pip install rich textual click")

if __name__ == "__main__":
    main()