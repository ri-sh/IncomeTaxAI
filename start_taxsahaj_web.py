#!/usr/bin/env python3
"""
TaxSahaj Web Server Launcher
============================

Easy launcher script for the enhanced TaxSahaj web interface.
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def check_requirements():
    """Check if required packages are installed"""
    required_packages = ['flask', 'werkzeug']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("🚨 Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n💡 Install missing packages with:")
        print("   pip install flask werkzeug")
        return False
    
    return True

def start_web_server():
    """Start the TaxSahaj web server"""
    
    print("🚀 Starting TaxSahaj Enhanced Web Interface...")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Get the project directory
    project_dir = Path(__file__).parent
    web_server_path = project_dir / "src" / "web_server.py"
    
    if not web_server_path.exists():
        print(f"❌ Web server not found at: {web_server_path}")
        sys.exit(1)
    
    # Set environment variables
    os.environ['FLASK_ENV'] = 'development'
    os.environ['FLASK_DEBUG'] = '1'
    
    try:
        # Change to project directory
        os.chdir(project_dir)
        
        print("🌐 Starting web server at http://127.0.0.1:5000")
        print("📁 Upload folder: Temporary (auto-cleanup)")
        print("🔒 Privacy: All processing happens locally")
        print("💾 Data: Never stored permanently")
        print("\n" + "=" * 50)
        print("🎯 Ready to analyze your tax documents!")
        print("   1. Upload your documents (Form 16, bank statements, etc.)")
        print("   2. AI will process them locally on your device")
        print("   3. Get personalized tax recommendations")
        print("   4. Download detailed analysis report")
        print("=" * 50)
        
        # Open browser after a short delay
        def open_browser():
            time.sleep(2)  # Wait for server to start
            webbrowser.open('http://127.0.0.1:5000')
        
        import threading
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        # Start the Flask server
        subprocess.run([sys.executable, str(web_server_path)], cwd=project_dir)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down TaxSahaj web server...")
        print("🧹 Cleaning up temporary files...")
        print("✅ Goodbye! Your data remains private and secure.")
    except Exception as e:
        print(f"\n❌ Error starting web server: {e}")
        print("💡 Try running directly: python src/web_server.py")
        sys.exit(1)

if __name__ == "__main__":
    start_web_server()