import streamlit as st
import torch
from typing import Dict, Any, Optional, List
import os
from dataclasses import dataclass

@dataclass
class ModelConfig:
    """Configuration for different models"""
    name: str
    model_id: str
    description: str
    best_for: List[str]
    device: str
    framework: str
    memory_requirement: str
    speed: str
    accuracy: str
    is_available: bool = True

class ModelSelector:
    """Model selection system for different document types"""
    
    def __init__(self):
        self.models = self._initialize_models()
        self.current_model = None
    
    def _initialize_models(self) -> Dict[str, ModelConfig]:
        """Initialize available models"""
        # Detect available device
        device = self._detect_device()
        
        models = {
            # OCR and Document Understanding Models
            "donut": ModelConfig(
                name="Donut (Document Understanding Transformer)",
                model_id="naver-clova-ix/donut-base",
                description="OCR-free document understanding model, excellent for structured forms",
                best_for=["form_16", "form_16a", "structured_forms"],
                device=device,
                framework="PyTorch + Transformers",
                memory_requirement="2-4 GB",
                speed="Fast",
                accuracy="High (95%+)"
            ),
            
            "layoutlmv3": ModelConfig(
                name="LayoutLMv3",
                model_id="microsoft/layoutlmv3-base",
                description="Multi-modal document understanding with text, layout, and image",
                best_for=["form_16", "form_16a", "complex_documents"],
                device=device,
                framework="PyTorch + Transformers",
                memory_requirement="3-6 GB",
                speed="Medium",
                accuracy="Very High (97%+)"
            ),
            
            "monkey_ocr": ModelConfig(
                name="MonkeyOCR-MLX",
                model_id="mlx-community/monkey-ocr-mlx",
                description="Fast OCR optimized for Apple Silicon with MLX framework",
                best_for=["general_ocr", "text_extraction", "mac_optimized"],
                device="mps" if device == "mps" else "cpu",
                framework="MLX",
                memory_requirement="1-2 GB",
                speed="Very Fast",
                accuracy="High (90%+)"
            ),
            
            # Vision Language Models
            "qwen2_5_vl_3b": ModelConfig(
                name="Qwen 2.5 VL 3B",
                model_id="Qwen/Qwen2.5-VL-3B-Instruct",
                description="Efficient vision-language model for document understanding",
                best_for=["general_documents", "image_analysis", "multimodal"],
                device=device,
                framework="PyTorch + Transformers",
                memory_requirement="4-8 GB",
                speed="Medium",
                accuracy="High (92%+)"
            ),
            
            "qwen2_5_vl_7b": ModelConfig(
                name="Qwen 2.5 VL 7B",
                model_id="Qwen/Qwen2.5-VL-7B-Instruct",
                description="High-performance vision-language model for complex documents",
                best_for=["complex_documents", "detailed_analysis", "high_accuracy"],
                device=device,
                framework="PyTorch + Transformers",
                memory_requirement="8-16 GB",
                speed="Slow",
                accuracy="Very High (96%+)"
            ),
            
            # Current Models
            "ollama_llm": ModelConfig(
                name="Ollama LLM (Current)",
                model_id="gpt-oss-20b",
                description="Current LLM-based document analysis",
                best_for=["general_analysis", "text_based", "conversational"],
                device="cpu",
                framework="Ollama",
                memory_requirement="4-8 GB",
                speed="Medium",
                accuracy="Good (85%+)"
            ),
            
            "llamaindex_rag": ModelConfig(
                name="LlamaIndex RAG (Current)",
                model_id="sentence-transformers/all-MiniLM-L6-v2",
                description="Current RAG-based knowledge retrieval",
                best_for=["knowledge_retrieval", "tax_qa", "context_aware"],
                device="cpu",
                framework="LlamaIndex",
                memory_requirement="2-4 GB",
                speed="Fast",
                accuracy="Good (88%+)"
            )
        }
        
        # Check model availability
        for model_key, model_config in models.items():
            model_config.is_available = self._check_model_availability(model_config)
        
        return models
    
    def _detect_device(self) -> str:
        """Detect the best available device"""
        if torch.backends.mps.is_available():
            return "mps"
        elif torch.cuda.is_available():
            return "cuda"
        else:
            return "cpu"
    
    def _check_model_availability(self, model_config: ModelConfig) -> bool:
        """Check if a model is available for use"""
        try:
            # Check if required packages are installed
            if "mlx" in model_config.framework.lower():
                import mlx
                return True
            elif "torch" in model_config.framework.lower():
                import torch
                return True
            elif "transformers" in model_config.framework.lower():
                from transformers import AutoTokenizer
                return True
            else:
                return True
        except ImportError:
            return False
    
    def show_model_selection_interface(self) -> None:
        """Show the model selection interface in Streamlit"""
        st.subheader("🤖 AI Model Selection")
        
        # Model selection tabs
        tab1, tab2, tab3 = st.tabs(["📄 Document Models", "👁️ Vision Models", "⚙️ Current Models"])
        
        with tab1:
            self._show_document_models()
        
        with tab2:
            self._show_vision_models()
        
        with tab3:
            self._show_current_models()
        
        # Model recommendations
        self._show_model_recommendations()
    
    def _show_document_models(self) -> None:
        """Show document understanding models"""
        st.markdown("### 📄 Document Understanding Models")
        
        # Donut Model
        with st.expander("🔍 Donut (Document Understanding Transformer)", expanded=True):
            model = self.models["donut"]
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"""
                **{model.name}**
                
                {model.description}
                
                **Best for:** {', '.join(model.best_for)}
                **Framework:** {model.framework}
                **Memory:** {model.memory_requirement}
                **Speed:** {model.speed}
                **Accuracy:** {model.accuracy}
                """)
            
            with col2:
                if model.is_available:
                    if st.button("🚀 Use Donut", key="donut_btn"):
                        self.current_model = "donut"
                        st.success("✅ Donut model selected for Form 16 analysis!")
                else:
                    st.warning("⚠️ Requires: `pip install transformers torch`")
        
        # LayoutLMv3 Model
        with st.expander("📋 LayoutLMv3 (Multi-modal Document Understanding)"):
            model = self.models["layoutlmv3"]
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"""
                **{model.name}**
                
                {model.description}
                
                **Best for:** {', '.join(model.best_for)}
                **Framework:** {model.framework}
                **Memory:** {model.memory_requirement}
                **Speed:** {model.speed}
                **Accuracy:** {model.accuracy}
                """)
            
            with col2:
                if model.is_available:
                    if st.button("🚀 Use LayoutLMv3", key="layoutlmv3_btn"):
                        self.current_model = "layoutlmv3"
                        st.success("✅ LayoutLMv3 model selected!")
                else:
                    st.warning("⚠️ Requires: `pip install transformers torch`")
        
        # MonkeyOCR Model
        with st.expander("🐒 MonkeyOCR-MLX (Apple Silicon Optimized)"):
            model = self.models["monkey_ocr"]
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"""
                **{model.name}**
                
                {model.description}
                
                **Best for:** {', '.join(model.best_for)}
                **Framework:** {model.framework}
                **Memory:** {model.memory_requirement}
                **Speed:** {model.speed}
                **Accuracy:** {model.accuracy}
                """)
            
            with col2:
                if model.is_available:
                    if st.button("🚀 Use MonkeyOCR", key="monkey_btn"):
                        self.current_model = "monkey_ocr"
                        st.success("✅ MonkeyOCR model selected!")
                else:
                    st.warning("⚠️ Requires: `pip install mlx`")
    
    def _show_vision_models(self) -> None:
        """Show vision-language models"""
        st.markdown("### 👁️ Vision-Language Models")
        
        # Qwen 2.5 VL 3B
        with st.expander("🖼️ Qwen 2.5 VL 3B (Efficient Vision-Language)", expanded=True):
            model = self.models["qwen2_5_vl_3b"]
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"""
                **{model.name}**
                
                {model.description}
                
                **Best for:** {', '.join(model.best_for)}
                **Framework:** {model.framework}
                **Memory:** {model.memory_requirement}
                **Speed:** {model.speed}
                **Accuracy:** {model.accuracy}
                """)
            
            with col2:
                if model.is_available:
                    if st.button("🚀 Use Qwen 2.5 VL 3B", key="qwen3b_btn"):
                        self.current_model = "qwen2_5_vl_3b"
                        st.success("✅ Qwen 2.5 VL 3B model selected!")
                else:
                    st.warning("⚠️ Requires: `pip install transformers torch`")
        
        # Qwen 2.5 VL 7B
        with st.expander("🖼️ Qwen 2.5 VL 7B (High-Performance Vision-Language)"):
            model = self.models["qwen2_5_vl_7b"]
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"""
                **{model.name}**
                
                {model.description}
                
                **Best for:** {', '.join(model.best_for)}
                **Framework:** {model.framework}
                **Memory:** {model.memory_requirement}
                **Speed:** {model.speed}
                **Accuracy:** {model.accuracy}
                """)
            
            with col2:
                if model.is_available:
                    if st.button("🚀 Use Qwen 2.5 VL 7B", key="qwen7b_btn"):
                        self.current_model = "qwen2_5_vl_7b"
                        st.success("✅ Qwen 2.5 VL 7B model selected!")
                else:
                    st.warning("⚠️ Requires: `pip install transformers torch`")
    
    def _show_current_models(self) -> None:
        """Show current models"""
        st.markdown("### ⚙️ Current Models")
        
        # Ollama LLM
        with st.expander("💬 Ollama LLM (Current)", expanded=True):
            model = self.models["ollama_llm"]
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"""
                **{model.name}**
                
                {model.description}
                
                **Best for:** {', '.join(model.best_for)}
                **Framework:** {model.framework}
                **Memory:** {model.memory_requirement}
                **Speed:** {model.speed}
                **Accuracy:** {model.accuracy}
                """)
            
            with col2:
                if st.button("🔄 Use Current LLM", key="ollama_btn"):
                    self.current_model = "ollama_llm"
                    st.success("✅ Current Ollama LLM selected!")
        
        # LlamaIndex RAG
        with st.expander("🔍 LlamaIndex RAG (Current)"):
            model = self.models["llamaindex_rag"]
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"""
                **{model.name}**
                
                {model.description}
                
                **Best for:** {', '.join(model.best_for)}
                **Framework:** {model.framework}
                **Memory:** {model.memory_requirement}
                **Speed:** {model.speed}
                **Accuracy:** {model.accuracy}
                """)
            
            with col2:
                if st.button("🔄 Use Current RAG", key="rag_btn"):
                    self.current_model = "llamaindex_rag"
                    st.success("✅ Current LlamaIndex RAG selected!")
    
    def _show_model_recommendations(self) -> None:
        """Show model recommendations based on document type"""
        st.subheader("🎯 Model Recommendations")
        
        # Document type selection
        doc_type = st.selectbox(
            "Select your document type:",
            ["form_16", "form_16a", "bank_statement", "investment_proof", "capital_gains", "general"],
            help="Choose the type of document you want to analyze"
        )
        
        # Get recommendations
        recommendations = self._get_recommendations(doc_type)
        
        st.markdown("### 📊 Recommended Models:")
        
        for i, (model_key, score, reason) in enumerate(recommendations):
            model = self.models[model_key]
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"**{i+1}. {model.name}**")
                st.markdown(f"*{reason}*")
            
            with col2:
                st.metric("Score", f"{score:.1f}/10")
            
            with col3:
                if model.is_available:
                    if st.button(f"Use", key=f"rec_{model_key}"):
                        self.current_model = model_key
                        st.success(f"✅ {model.name} selected!")
                else:
                    st.warning("⚠️ Not available")
    
    def _get_recommendations(self, doc_type: str) -> List[tuple]:
        """Get model recommendations for a document type"""
        recommendations = []
        
        if doc_type == "form_16":
            recommendations = [
                ("donut", 9.5, "OCR-free, excellent for structured forms"),
                ("layoutlmv3", 9.0, "Multi-modal understanding with layout"),
                ("qwen2_5_vl_7b", 8.5, "High accuracy vision-language model"),
                ("ollama_llm", 7.0, "Current LLM-based approach")
            ]
        elif doc_type == "form_16a":
            recommendations = [
                ("donut", 9.0, "Structured form understanding"),
                ("layoutlmv3", 8.5, "Layout-aware analysis"),
                ("qwen2_5_vl_3b", 8.0, "Efficient vision-language"),
                ("ollama_llm", 7.0, "Current approach")
            ]
        elif doc_type in ["bank_statement", "investment_proof"]:
            recommendations = [
                ("monkey_ocr", 9.0, "Fast OCR for text extraction"),
                ("qwen2_5_vl_3b", 8.5, "Efficient document understanding"),
                ("layoutlmv3", 8.0, "Layout-aware analysis"),
                ("ollama_llm", 7.0, "Current approach")
            ]
        else:
            recommendations = [
                ("qwen2_5_vl_3b", 8.5, "General purpose vision-language"),
                ("monkey_ocr", 8.0, "Fast text extraction"),
                ("ollama_llm", 7.5, "Current LLM approach"),
                ("llamaindex_rag", 7.0, "Knowledge retrieval")
            ]
        
        return recommendations
    
    def get_current_model(self) -> Optional[str]:
        """Get the currently selected model"""
        return self.current_model
    
    def get_model_config(self, model_key: str) -> Optional[ModelConfig]:
        """Get configuration for a specific model"""
        return self.models.get(model_key)

# Global model selector instance
model_selector = ModelSelector() 