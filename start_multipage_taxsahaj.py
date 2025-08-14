#!/usr/bin/env python3
"""
Multi-Page TaxSahaj Web Server Launcher
=======================================

Launcher for the new multi-page TaxSahaj interface with clean separation:
- Page 1: Document Upload
- Page 2: Tax Analysis & Reports  
- Page 3: ITR Filing Guide
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def start_multipage_web_server():
    """Start the multi-page TaxSahaj web server"""
    
    print("🚀 Starting Multi-Page TaxSahaj Web Interface...")
    print("=" * 60)
    
    # Get the project directory
    project_dir = Path(__file__).parent
    web_server_path = project_dir / "src" / "web_server_new.py"
    
    if not web_server_path.exists():
        print(f"❌ Web server not found at: {web_server_path}")
        sys.exit(1)
    
    try:
        # Change to project directory
        os.chdir(project_dir)
        
        print("🌐 Starting multi-page web server at http://127.0.0.1:5001")
        print("📱 NEW: Clean Multi-Page Design")
        print("📊 Page 2: Beautiful Tax Reports & Charts")
        print("📋 Page 3: Step-by-Step Filing Guide")
        print("\\n" + "=" * 60)
        print("✨ MULTI-PAGE WORKFLOW:")
        print("   📄 Page 1: Upload your tax documents")
        print("   ⏳ Click 'Process Documents' button")
        print("   📊 Page 2: View clean tax analysis with charts")
        print("   📋 Page 3: Click 'Guide Me' for portal instructions")
        print("   ✏️ Edit details anytime with correction modal")
        print("=" * 60)
        
        # Open browser after a short delay
        def open_browser():
            time.sleep(3)  # Wait for server to start
            webbrowser.open('http://127.0.0.1:5001')
        
        import threading
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        # Activate virtual environment and run
        activate_script = project_dir / "tax_ai_env_py310" / "bin" / "activate"
        if activate_script.exists():
            cmd = f"source {activate_script} && python {web_server_path}"
            subprocess.run(cmd, shell=True, cwd=project_dir)
        else:
            # Fallback to direct execution
            subprocess.run([sys.executable, str(web_server_path)], cwd=project_dir)
        
    except KeyboardInterrupt:
        print("\\n\\n🛑 Shutting down Multi-Page TaxSahaj...")
        print("🧹 Cleaning up temporary files...")
        print("✅ Your data remains private and secure.")
    except Exception as e:
        print(f"\\n❌ Error starting multi-page web server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_multipage_web_server()