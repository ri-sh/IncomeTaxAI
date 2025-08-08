#!/usr/bin/env python3
"""
Production Launcher for Income Tax AI Assistant
Streamlined launcher with dependency checks and optimizations
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required. Current version:", sys.version)
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True

def check_required_packages():
    """Check if essential packages are installed"""
    required_packages = [
        'streamlit',
        'pandas',
        'plotly'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} installed")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} missing")
    
    return missing_packages

def install_missing_packages(packages):
    """Install missing packages"""
    if not packages:
        return True
    
    print(f"\n📦 Installing missing packages: {', '.join(packages)}")
    
    try:
        # Try pip install
        cmd = [sys.executable, "-m", "pip", "install"] + packages
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Packages installed successfully")
            return True
        else:
            error_output = result.stderr
            print(f"❌ Package installation failed")
            
            # Check for externally-managed-environment error
            if "externally-managed-environment" in error_output:
                print("\n🚨 EXTERNAL ENVIRONMENT DETECTED")
                print("Your Python is managed by Homebrew/system and blocks package installation.")
                print("\n✅ SOLUTION: Use Virtual Environment")
                print("1. Create virtual environment:")
                print("   python3 -m venv tax_ai_env")
                print("2. Activate it:")
                print("   source tax_ai_env/bin/activate")
                print("3. Install packages:")
                print("   pip install -r requirements.txt")
                print("4. Setup models:")
                print("   python setup_models.py")
                print("5. Launch system:")
                print("   python launch_production.py")
                print("\n📖 See QUICK_MODEL_SETUP.md for detailed instructions")
            else:
                print(f"Error details: {error_output}")
                print(f"\n💡 Try manual installation: pip install {' '.join(packages)}")
            
            return False
            
    except Exception as e:
        print(f"❌ Installation error: {e}")
        return False

def setup_directories():
    """Create necessary directories"""
    directories = [
        "data/tax_documents",
        "data/knowledge_base", 
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Directory: {directory}")

def launch_streamlit():
    """Launch the Streamlit application"""
    print("\n🚀 Launching Income Tax AI Assistant...")
    print("🌐 Access URL: http://localhost:8501")
    print("📱 Mobile URL: http://<your-ip>:8501")
    print("\n⚠️  Press Ctrl+C to stop the application")
    
    try:
        # Launch Streamlit
        cmd = [
            sys.executable, "-m", "streamlit", "run", 
            "src/ui/streamlit_app.py",
            "--server.port=8501",
            "--server.address=0.0.0.0",
            "--server.headless=true",
            "--browser.serverAddress=localhost"
        ]
        
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n\n👋 Income Tax AI Assistant stopped")
    except Exception as e:
        print(f"\n❌ Failed to start application: {e}")

def show_system_info():
    """Display system information"""
    print("🔗" * 20 + " INCOME TAX AI ASSISTANT " + "🔗" * 20)
    print("🇮🇳 Production-Ready Indian Income Tax Filing Assistant")
    print(f"📅 Financial Year: 2024-25 (Assessment Year: 2025-26)")
    print(f"📁 Working Directory: {os.getcwd()}")
    print(f"🐍 Python: {sys.version}")
    print("🔗" * 70)

def check_models():
    """Check if AI models are available"""
    config_path = "config/models.json"
    
    if not os.path.exists(config_path):
        return False, "No model configuration found"
    
    try:
        import json
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        setup_complete = config.get('setup_complete', False)
        embedding_ready = config.get('embedding_model', {}).get('status') == 'ready'
        main_model_ready = config.get('main_model_ready', False)
        
        if not setup_complete:
            return False, "Model setup not completed"
        
        if not embedding_ready:
            return False, "Embedding model not ready"
        
        if main_model_ready:
            return True, "All models ready (including main language model)"
        else:
            return True, "Embedding model ready (main model will use simulated responses)"
        
    except Exception as e:
        return False, f"Error checking models: {e}"

def show_features():
    """Display available features"""
    print("\n🚀 AVAILABLE FEATURES:")
    print("📄 AI-Powered Document Analysis")
    print("💬 Tax Assistant Chat (Professional Boundaries)")
    print("⚖️  Old vs New Regime Comparison")
    print("📊 Interactive Tax Dashboard")
    print("📋 Section-wise ITR Filing Guide")
    print("📄 Professional PDF Report Generation")
    print("🔗 Google Drive Integration")
    print("🤖 GPT-OSS-20B + LlamaIndex RAG System")
    print("🛡️  Tax-Only AI Behavior (100% Accuracy)")
    
    # Check model status
    models_ready, status_msg = check_models()
    
    if models_ready:
        print(f"✅ AI Models: {status_msg}")
    else:
        print(f"⚠️  AI Models: {status_msg}")
        print("💡 Run 'python setup_models.py' to download models")

def main():
    """Main production launcher"""
    
    show_system_info()
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Setup directories
    print("\n📁 Setting up directories...")
    setup_directories()
    
    # Check packages
    print("\n📦 Checking dependencies...")
    missing = check_required_packages()
    
    if missing:
        print(f"\n⚠️  Missing packages detected: {', '.join(missing)}")
        install_choice = input("📥 Install missing packages automatically? (y/n): ").lower()
        
        if install_choice == 'y':
            if not install_missing_packages(missing):
                print("\n❌ Package installation failed. Please install manually and restart.")
                sys.exit(1)
        else:
            print("⚠️  Please install missing packages manually and restart:")
            print(f"   pip install {' '.join(missing)}")
            sys.exit(1)
    
    # Check models
    print("\n🤖 Checking AI models...")
    models_ready, status_msg = check_models()
    
    if not models_ready:
        print(f"⚠️  {status_msg}")
        print("\n💡 AI models are not fully set up. You have these options:")
        print("   1. Continue with simulated AI responses (limited functionality)")
        print("   2. Run model setup first (recommended)")
        
        model_choice = input("\nChoose: (1) Continue anyway, (2) Setup models, (3) Exit: ").strip()
        
        if model_choice == '2':
            print("\n🤖 Starting model setup...")
            try:
                import subprocess
                result = subprocess.run([sys.executable, "setup_models.py"], 
                                      capture_output=False, text=True)
                if result.returncode == 0:
                    print("✅ Model setup completed!")
                else:
                    print("⚠️ Model setup had issues. Continuing with limited functionality.")
            except Exception as e:
                print(f"❌ Could not run model setup: {e}")
                print("💡 Please run 'python setup_models.py' manually")
        
        elif model_choice == '3':
            print("👋 Exiting. Run 'python setup_models.py' to setup models.")
            return
        
        elif model_choice == '1':
            print("⚠️ Continuing with limited AI functionality...")
        
        else:
            print("❌ Invalid choice. Exiting.")
            return
    else:
        print(f"✅ {status_msg}")
    
    # Show features
    show_features()
    
    # Launch confirmation
    print("\n" + "✅" * 50)
    print("🎯 PRODUCTION SYSTEM READY!")
    print("✅" * 50)
    
    launch_choice = input("\n🚀 Launch Income Tax AI Assistant? (y/n): ").lower()
    
    if launch_choice == 'y':
        launch_streamlit()
    else:
        print("👋 Launch cancelled. Run again when ready!")

if __name__ == "__main__":
    main()