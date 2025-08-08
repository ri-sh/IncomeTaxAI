"""Configuration settings for the Income Tax Assistant."""

import os
from typing import Optional
from dataclasses import dataclass

@dataclass
class ModelConfig:
    """Configuration for the GPT-OSS-20B model."""
    model_name: str = "openai/gpt-oss-20b"
    device_map: str = "auto"
    torch_dtype: str = "auto"
    max_new_tokens: int = 512
    temperature: float = 0.1
    reasoning_level: str = "medium"  # low, medium, high

@dataclass
class VectorDBConfig:
    """Configuration for vector database."""
    collection_name: str = "tax_knowledge"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int = 512
    chunk_overlap: int = 50
    persist_directory: str = "./data/knowledge_base"

@dataclass
class AppConfig:
    """Main application configuration."""
    app_title: str = "Income Tax AI Assistant"
    app_description: str = "AI-powered assistant for income tax queries and calculations"
    debug: bool = False
    max_chat_history: int = 20

# Environment variables
MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", "./models_cache")
DATA_DIR = os.getenv("DATA_DIR", "./data")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Default configurations
model_config = ModelConfig()
vectordb_config = VectorDBConfig()
app_config = AppConfig()