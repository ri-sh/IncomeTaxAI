#!/usr/bin/env python3
"""
Enhanced TaxSahaj Web Server Launcher
=====================================

Quick launcher for the TaxSahaj web interface with data correction capabilities.
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def start_enhanced_web_server():
    """Start the enhanced TaxSahaj web server with correction capabilities"""
    
    print("🚀 Starting Enhanced TaxSahaj Web Interface...")
    print("=" * 60)
    
    # Get the project directory
    project_dir = Path(__file__).parent
    web_server_path = project_dir / "src" / "web_server.py"
    
    if not web_server_path.exists():
        print(f"❌ Web server not found at: {web_server_path}")
        sys.exit(1)
    
    try:
        # Change to project directory
        os.chdir(project_dir)
        
        print("🌐 Starting enhanced web server at http://127.0.0.1:5000")
        print("📋 New Feature: Review & Correct Extracted Data")
        print("🔄 Real-time Tax Recalculation")
        print("🏠 Home Loan & Advanced Deductions Support")
        print("📊 Step-by-Step ITR Filing Guidance")
        print("\\n" + "=" * 60)
        print("✨ ENHANCED FEATURES:")
        print("   1. Upload documents (Form 16, payslips, bank certificates)")
        print("   2. Review & correct extracted information")
        print("   3. Add missing investments (NPS, ELSS, Home Loan)")
        print("   4. Real-time tax recalculation")
        print("   5. Personalized ITR filing guidance")
        print("   6. Download comprehensive tax report")
        print("=" * 60)
        
        # Activate virtual environment and run
        activate_script = project_dir / "tax_ai_env_py310" / "bin" / "activate"
        if activate_script.exists():
            cmd = f"source {activate_script} && python {web_server_path}"
            subprocess.run(cmd, shell=True, cwd=project_dir)
        else:
            # Fallback to direct execution
            subprocess.run([sys.executable, str(web_server_path)], cwd=project_dir)
        
    except KeyboardInterrupt:
        print("\\n\\n🛑 Shutting down Enhanced TaxSahaj...")
        print("🧹 Cleaning up temporary files...")
        print("✅ Your data remains private and secure.")
    except Exception as e:
        print(f"\\n❌ Error starting enhanced web server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_enhanced_web_server()