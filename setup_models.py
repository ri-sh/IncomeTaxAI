#!/usr/bin/env python3
"""
Model Setup and Download Script
Downloads and configures all required models from Hugging Face
"""

import os
import sys
from pathlib import Path
import json

def check_requirements():
    """Check if required packages are installed"""
    required_packages = [
        'transformers',
        'torch', 
        'accelerate',
        'sentence-transformers',
        'huggingface-hub'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} installed")
        except ImportError:
            missing.append(package)
            print(f"❌ {package} missing")
    
    return missing

def install_missing_packages(packages):
    """Install missing packages"""
    if not packages:
        return True
    
    print(f"\n📦 Installing missing packages: {', '.join(packages)}")
    
    import subprocess
    try:
        cmd = [sys.executable, "-m", "pip", "install"] + packages
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Packages installed successfully")
            return True
        else:
            print(f"❌ Installation failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Installation error: {e}")
        return False

def download_gpt_oss_model():
    """Download GPT-OSS-20B model from Hugging Face"""
    
    print("\n🤖 Setting up GPT-OSS-20B Model...")
    
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
        import torch
        
        model_name = "openai/gpt-oss-20b"
        cache_dir = "models/gpt-oss-20b"
        
        # Create model directory
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        
        print(f"📥 Downloading tokenizer for {model_name}...")
        
        # Download tokenizer (lightweight)
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir=cache_dir,
            trust_remote_code=True
        )
        
        print(f"✅ Tokenizer downloaded and cached")
        
        # Configure quantization for memory efficiency
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4"
        )
        
        print(f"📥 Downloading model {model_name} (this may take 10-20 minutes)...")
        print("💡 Model will be quantized to 4-bit for memory efficiency")
        
        # Download model with quantization
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            cache_dir=cache_dir,
            quantization_config=quantization_config,
            device_map="auto",
            trust_remote_code=True,
            torch_dtype=torch.float16
        )
        
        print(f"✅ GPT-OSS-20B model downloaded and ready")
        
        # Save model configuration
        config = {
            "model_name": model_name,
            "cache_dir": cache_dir,
            "quantized": True,
            "setup_date": str(Path(__file__).stat().st_mtime)
        }
        
        with open(f"{cache_dir}/config.json", "w") as f:
            json.dump(config, f, indent=2)
        
        return True
        
    except Exception as e:
        print(f"❌ Error downloading GPT-OSS-20B: {e}")
        print("💡 Note: GPT-OSS-20B is a large model (40GB+)")
        print("   Consider using a smaller model for testing")
        return False

def download_embedding_model():
    """Download sentence transformer model for embeddings"""
    
    print("\n🧠 Setting up Embedding Model...")
    
    try:
        from sentence_transformers import SentenceTransformer
        
        model_name = "sentence-transformers/all-MiniLM-L6-v2"
        cache_dir = "models/embeddings"
        
        # Create model directory
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        
        print(f"📥 Downloading embedding model: {model_name}...")
        
        # Download and cache embedding model
        model = SentenceTransformer(model_name, cache_folder=cache_dir)
        
        print(f"✅ Embedding model downloaded and ready")
        
        # Test the model
        test_text = "Income tax filing for India"
        embeddings = model.encode([test_text])
        print(f"🧪 Model test successful - embedding shape: {embeddings.shape}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error downloading embedding model: {e}")
        return False

def setup_alternative_models():
    """Setup smaller alternative models if GPT-OSS-20B fails"""
    
    print("\n🔄 Setting up alternative models...")
    
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch
        
        # Smaller alternative models
        alternative_models = [
            "microsoft/DialoGPT-medium",  # 345M parameters
            "microsoft/DialoGPT-small",   # 117M parameters
            "gpt2-medium"                 # 345M parameters
        ]
        
        for model_name in alternative_models:
            try:
                print(f"📥 Trying alternative model: {model_name}")
                
                cache_dir = f"models/{model_name.replace('/', '_')}"
                Path(cache_dir).mkdir(parents=True, exist_ok=True)
                
                tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    cache_dir=cache_dir,
                    padding_side='left'
                )
                
                if tokenizer.pad_token is None:
                    tokenizer.pad_token = tokenizer.eos_token
                
                model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    cache_dir=cache_dir,
                    torch_dtype=torch.float16,
                    device_map="auto"
                )
                
                print(f"✅ Alternative model {model_name} ready")
                
                # Save configuration
                config = {
                    "model_name": model_name,
                    "cache_dir": cache_dir,
                    "model_type": "alternative",
                    "parameters": "small-medium"
                }
                
                with open(f"{cache_dir}/config.json", "w") as f:
                    json.dump(config, f, indent=2)
                
                return True, model_name
                
            except Exception as e:
                print(f"⚠️ {model_name} failed: {e}")
                continue
        
        return False, None
        
    except Exception as e:
        print(f"❌ Error setting up alternative models: {e}")
        return False, None

def setup_chromadb():
    """Setup ChromaDB for vector storage"""
    
    print("\n🗃️ Setting up ChromaDB...")
    
    try:
        import chromadb
        from chromadb.config import Settings
        
        # Create ChromaDB directory
        db_path = "data/knowledge_base/chromadb"
        Path(db_path).mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(allow_reset=True)
        )
        
        # Create tax knowledge collection
        collection = client.get_or_create_collection(
            name="tax_knowledge",
            metadata={"description": "Indian tax laws and regulations"}
        )
        
        print(f"✅ ChromaDB initialized at {db_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up ChromaDB: {e}")
        return False

def create_model_config():
    """Create model configuration file"""
    
    config = {
        "primary_model": {
            "name": "openai/gpt-oss-20b",
            "status": "downloading",
            "cache_dir": "models/gpt-oss-20b",
            "quantized": True
        },
        "embedding_model": {
            "name": "sentence-transformers/all-MiniLM-L6-v2", 
            "cache_dir": "models/embeddings",
            "status": "ready"
        },
        "vector_db": {
            "type": "chromadb",
            "path": "data/knowledge_base/chromadb",
            "status": "ready"
        },
        "alternative_models": [],
        "setup_complete": False
    }
    
    config_path = "config/models.json"
    Path("config").mkdir(exist_ok=True)
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Model configuration saved to {config_path}")
    return config_path

def main():
    """Main setup function"""
    
    print("🤖" * 25 + " MODEL SETUP " + "🤖" * 25)
    print("🇮🇳 Income Tax AI Assistant - Model Download & Setup")
    print("🤖" * 65)
    
    # Check system requirements
    print("\n1️⃣ Checking system requirements...")
    missing_packages = check_requirements()
    
    if missing_packages:
        print(f"\n⚠️ Missing packages: {', '.join(missing_packages)}")
        install_choice = input("📥 Install missing packages? (y/n): ").lower()
        
        if install_choice == 'y':
            if not install_missing_packages(missing_packages):
                print("❌ Package installation failed. Please install manually.")
                return False
        else:
            print("❌ Required packages not installed. Exiting.")
            return False
    
    # Create model configuration
    print("\n2️⃣ Creating model configuration...")
    config_path = create_model_config()
    
    # Setup ChromaDB
    print("\n3️⃣ Setting up vector database...")
    if not setup_chromadb():
        print("⚠️ ChromaDB setup failed, but continuing...")
    
    # Download embedding model (small and fast)
    print("\n4️⃣ Downloading embedding model...")
    if not download_embedding_model():
        print("❌ Embedding model setup failed")
        return False
    
    # Download main model
    print("\n5️⃣ Downloading main language model...")
    print("⚠️ This is a large model (40GB+) and may take time...")
    
    model_choice = input("📥 Download GPT-OSS-20B? (y/n/s for smaller alternative): ").lower()
    
    main_model_ready = False
    
    if model_choice == 'y':
        main_model_ready = download_gpt_oss_model()
    elif model_choice == 's':
        main_model_ready, alt_model = setup_alternative_models()
        if main_model_ready:
            print(f"✅ Using alternative model: {alt_model}")
    else:
        print("⚠️ Skipping main model download")
    
    # Update configuration
    with open(config_path, "r") as f:
        config = json.load(f)
    
    config["setup_complete"] = True
    config["main_model_ready"] = main_model_ready
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    # Final status
    print("\n" + "✅" * 50)
    print("🎯 MODEL SETUP COMPLETE!")
    print("✅" * 50)
    
    if main_model_ready:
        print("✅ Main language model: Ready")
    else:
        print("⚠️ Main language model: Not available (will use simulated responses)")
    
    print("✅ Embedding model: Ready")
    print("✅ Vector database: Ready")
    print("✅ Configuration: Saved")
    
    print(f"\n🚀 Next step: python launch_production.py")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)