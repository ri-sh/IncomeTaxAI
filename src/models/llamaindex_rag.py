"""
LlamaIndex RAG (Retrieval Augmented Generation) for Income Tax AI
Handles document indexing, retrieval, and context-aware question answering
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
import uuid

# LlamaIndex imports
from llama_index.core import (
    VectorStoreIndex, 
    SimpleDirectoryReader, 
    Document,
    Settings,
    StorageContext,
    load_index_from_storage
)
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.callbacks import CallbackManager, LlamaDebugHandler
from llama_index.llms.ollama import Ollama

# Vector store
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

@dataclass
class TaxDocument:
    """Represents a tax document in the knowledge base"""
    doc_id: str
    file_path: str
    doc_type: str
    content: str
    metadata: Dict[str, Any]
    processed_date: str

class TaxKnowledgeBase:
    """LlamaIndex-powered knowledge base for Indian tax documents"""
    
    def __init__(self, 
                 knowledge_base_path: str = None,
                 embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        
        self.knowledge_base_path = knowledge_base_path or "data/knowledge_base"
        self.chroma_path = os.path.join(self.knowledge_base_path, "chroma_db")
        self.index_path = os.path.join(self.knowledge_base_path, "llama_index")
        
        # Create directories
        os.makedirs(self.knowledge_base_path, exist_ok=True)
        os.makedirs(self.chroma_path, exist_ok=True)
        os.makedirs(self.index_path, exist_ok=True)
        
        # Initialize embedding model with local cache check
        embedding_cache_dir = self._get_embedding_cache_dir()
        
        try:
            if embedding_cache_dir and os.path.exists(embedding_cache_dir):
                print(f"📥 Loading embedding model from cache: {embedding_cache_dir}")
                self.embedding_model = HuggingFaceEmbedding(
                    model_name=embedding_model,
                    cache_folder=embedding_cache_dir
                )
            else:
                print(f"📥 Loading embedding model: {embedding_model}")
                self.embedding_model = HuggingFaceEmbedding(model_name=embedding_model)
                print("⚠️ Model will be downloaded on first use")
                print("💡 Run 'python setup_models.py' to pre-download models")
        
        except Exception as e:
            print(f"❌ Error loading embedding model: {e}")
            print("💡 Falling back to simulated embeddings")
            self.embedding_model = None
        
        # Set global settings
        if self.embedding_model:
            Settings.embed_model = self.embedding_model
            
        # Configure Ollama LLM for intelligent responses
        try:
            ollama_llm = Ollama(
                model="llama2",
                base_url="http://localhost:11434",
                request_timeout=120.0,  # Longer timeout for better responses
                temperature=0.2,  # Slightly higher for more natural responses
                context_window=4096,  # Larger context window
                num_predict=1024  # More detailed responses
            )
            Settings.llm = ollama_llm
            print("✅ Ollama LLM configured with Llama2 model")
        except Exception as e:
            print(f"⚠️ Could not configure Ollama: {e}")
            print("💡 Falling back to retrieval-only mode")
            Settings.llm = None
            
        Settings.chunk_size = 512
        Settings.chunk_overlap = 50
        
        # Initialize components
        self.index = None
        self.query_engine = None
        self.retriever = None
        self.documents_db = {}
        
        # Debug handler
        self.llama_debug = LlamaDebugHandler(print_trace_on_end=True)
        Settings.callback_manager = CallbackManager([self.llama_debug])
        
        # Load existing index if available
        self._load_or_create_index()
    
    def _get_embedding_cache_dir(self):
        """Get the local cache directory for embedding models"""
        config_path = "config/models.json"
        
        if not os.path.exists(config_path):
            return None
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            embedding_config = config.get('embedding_model', {})
            if embedding_config.get('status') == 'ready':
                return embedding_config.get('cache_dir')
        
        except Exception as e:
            print(f"⚠️ Error reading model config: {e}")
        
        return None
    
    def _load_or_create_index(self):
        """Load existing index or create new one"""
        try:
            if os.path.exists(os.path.join(self.index_path, "index_store.json")):
                print("📚 Loading existing knowledge base...")
                storage_context = StorageContext.from_defaults(persist_dir=self.index_path)
                self.index = load_index_from_storage(storage_context)
                print("✅ Knowledge base loaded successfully")
            else:
                print("🆕 Creating new knowledge base...")
                self._create_initial_knowledge_base()
        except Exception as e:
            print(f"⚠️ Error loading index: {e}")
            print("🆕 Creating new knowledge base...")
            self._create_initial_knowledge_base()
        
        self._setup_query_engine()
    
    def _create_initial_knowledge_base(self):
        """Create initial knowledge base with tax law documents"""
        
        # Initialize ChromaDB
        chroma_client = chromadb.PersistentClient(path=self.chroma_path)
        chroma_collection = chroma_client.get_or_create_collection("tax_documents")
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        
        # Create storage context
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # Load initial tax knowledge documents
        initial_docs = self._create_initial_tax_documents()
        
        if initial_docs:
            # Create index from documents
            self.index = VectorStoreIndex.from_documents(
                initial_docs,
                storage_context=storage_context
            )
            
            # Persist the index
            self.index.storage_context.persist(persist_dir=self.index_path)
            print("✅ Initial knowledge base created")
        else:
            # Create empty index
            self.index = VectorStoreIndex([], storage_context=storage_context)
            print("📝 Empty knowledge base created")
    
    def _create_initial_tax_documents(self) -> List[Document]:
        """Create initial tax knowledge documents"""
        
        documents = []
        
        # Load tax knowledge from our knowledge base file
        tax_knowledge_file = Path("data/tax_documents/indian_tax_knowledge_2024_25.md")
        
        if tax_knowledge_file.exists():
            try:
                with open(tax_knowledge_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Split into sections
                sections = content.split('##')
                
                for i, section in enumerate(sections[1:], 1):  # Skip first empty section
                    if section.strip():
                        title = section.split('\n')[0].strip()
                        section_content = section.strip()
                        
                        doc = Document(
                            text=section_content,
                            metadata={
                                "source": "indian_tax_knowledge_2024_25",
                                "section": title,
                                "doc_type": "tax_law",
                                "financial_year": "2024-25",
                                "section_number": i
                            },
                            id_=f"tax_law_section_{i}"
                        )
                        documents.append(doc)
                
                print(f"📚 Loaded {len(documents)} tax law sections")
                
            except Exception as e:
                print(f"⚠️ Error loading tax knowledge: {e}")
        
        # Add ITR form information
        itr_forms_info = self._create_itr_forms_documents()
        documents.extend(itr_forms_info)
        
        return documents
    
    def _create_itr_forms_documents(self) -> List[Document]:
        """Create documents about ITR forms"""
        
        itr_docs = []
        
        itr_info = {
            "ITR-1": {
                "description": "ITR-1 (Sahaj) is for individuals with salary income up to ₹50 lakh and income from one house property.",
                "eligible_income": ["Salary", "One house property", "Other sources up to ₹5000"],
                "not_eligible": ["Business income", "Capital gains", "Multiple house properties"],
                "due_date": "September 15, 2025"
            },
            "ITR-2": {
                "description": "ITR-2 is for individuals and HUFs with capital gains, multiple house properties, or foreign income.",
                "eligible_income": ["Salary", "House property", "Capital gains", "Foreign income"],
                "features": ["Schedule CG for capital gains", "Multiple employers", "Exempt income"],
                "due_date": "September 15, 2025"
            },
            "ITR-3": {
                "description": "ITR-3 is for individuals and HUFs having income from business or profession.",
                "eligible_income": ["Business income", "Professional income", "All other incomes"],
                "features": ["P&L statement", "Balance sheet", "Depreciation schedules"],
                "due_date": "October 31, 2025 (if audit required)"
            }
        }
        
        for form_name, info in itr_info.items():
            doc = Document(
                text=f"{form_name}: {info['description']}\n\nEligible Income: {', '.join(info['eligible_income'])}\n\nKey Features: {json.dumps(info, indent=2)}",
                metadata={
                    "source": "itr_forms_guide",
                    "form_name": form_name,
                    "doc_type": "itr_form",
                    "financial_year": "2024-25"
                },
                id_=f"itr_form_{form_name.lower()}"
            )
            itr_docs.append(doc)
        
        return itr_docs
    
    def _setup_query_engine(self):
        """Setup retriever and query engine"""
        if self.index:
            # Configure retriever
            self.retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=5  # Retrieve top 5 relevant chunks
            )
            
            # Configure post-processor
            similarity_postprocessor = SimilarityPostprocessor(similarity_cutoff=0.7)
            
            # Create query engine
            self.query_engine = RetrieverQueryEngine(
                retriever=self.retriever,
                node_postprocessors=[similarity_postprocessor]
            )
            
            print("🔧 Query engine configured")
    
    def add_user_document(self, file_path: str, doc_type: str = "user_document") -> bool:
        """Add user's tax document to knowledge base"""
        
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                print(f"❌ File not found: {file_path}")
                return False
            
            # Read document
            if file_path.suffix.lower() == '.pdf':
                documents = SimpleDirectoryReader(
                    input_files=[str(file_path)]
                ).load_data()
            else:
                # For other file types, read as text
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                documents = [Document(
                    text=content,
                    metadata={
                        "source": file_path.name,
                        "file_path": str(file_path),
                        "doc_type": doc_type,
                        "file_size": file_path.stat().st_size
                    },
                    id_=str(uuid.uuid4())
                )]
            
            # Add metadata to documents
            for doc in documents:
                doc.metadata.update({
                    "source": file_path.name,
                    "file_path": str(file_path),
                    "doc_type": doc_type,
                    "added_date": str(Path(file_path).stat().st_mtime)
                })
            
            # Add to index
            for doc in documents:
                self.index.insert(doc)
            
            # Persist updates
            self.index.storage_context.persist(persist_dir=self.index_path)
            
            print(f"✅ Added document: {file_path.name}")
            return True
            
        except Exception as e:
            print(f"❌ Error adding document {file_path}: {e}")
            return False
    
    def add_user_documents_batch(self, documents_path: str) -> Dict[str, int]:
        """Add all user documents from a directory"""
        
        documents_path = Path(documents_path)
        results = {"success": 0, "failed": 0, "total": 0}
        
        if not documents_path.exists():
            print(f"❌ Directory not found: {documents_path}")
            return results
        
        # Process all files in directory
        files = [f for f in documents_path.iterdir() if f.is_file() and not f.name.startswith('.')]
        results["total"] = len(files)
        
        print(f"📁 Processing {len(files)} documents from {documents_path.name}")
        
        for file_path in files:
            # Determine document type from filename
            doc_type = self._classify_document_type(file_path.name)
            
            if self.add_user_document(str(file_path), doc_type):
                results["success"] += 1
            else:
                results["failed"] += 1
        
        print(f"📊 Batch processing complete: {results['success']} success, {results['failed']} failed")
        return results
    
    def _classify_document_type(self, filename: str) -> str:
        """Classify document type from filename"""
        filename_lower = filename.lower()
        
        if "form16" in filename_lower or "form 16" in filename_lower:
            return "form_16"
        elif "elss" in filename_lower:
            return "elss_investment"
        elif "capital" in filename_lower and "gains" in filename_lower:
            return "capital_gains"
        elif "bank" in filename_lower and "interest" in filename_lower:
            return "bank_interest"
        elif "salary" in filename_lower:
            return "salary_document"
        elif "investment" in filename_lower:
            return "investment_proof"
        else:
            return "tax_document"
    
    def query_knowledge_base(self, question: str) -> Tuple[str, List[str]]:
        """Query the knowledge base and return answer with sources"""
        
        if not self.query_engine:
            return "Knowledge base not initialized.", []
        
        try:
            # Query the index
            response = self.query_engine.query(question)
            
            # Extract sources
            sources = []
            if hasattr(response, 'source_nodes'):
                for node in response.source_nodes:
                    if hasattr(node, 'metadata') and 'source' in node.metadata:
                        sources.append(node.metadata['source'])
            
            return str(response), list(set(sources))  # Remove duplicates
            
        except Exception as e:
            print(f"❌ Query error: {e}")
            return f"Error querying knowledge base: {e}", []
    
    def retrieve_context_for_question(self, question: str, max_chunks: int = 3) -> List[str]:
        """Retrieve relevant context chunks for a question"""
        
        if not self.retriever:
            return []
        
        try:
            # Retrieve relevant nodes
            nodes = self.retriever.retrieve(question)
            
            # Extract text content
            context_chunks = []
            for node in nodes[:max_chunks]:
                chunk_text = node.text if hasattr(node, 'text') else str(node)
                context_chunks.append(chunk_text)
            
            return context_chunks
            
        except Exception as e:
            print(f"❌ Context retrieval error: {e}")
            return []
    
    def get_document_statistics(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base"""
        
        if not self.index:
            return {"error": "Index not initialized"}
        
        try:
            # Get all nodes
            all_nodes = list(self.index.docstore.docs.values())
            
            # Count by document type
            doc_types = {}
            sources = set()
            
            for node in all_nodes:
                if hasattr(node, 'metadata'):
                    doc_type = node.metadata.get('doc_type', 'unknown')
                    doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
                    
                    source = node.metadata.get('source', 'unknown')
                    sources.add(source)
            
            return {
                "total_documents": len(all_nodes),
                "document_types": doc_types,
                "unique_sources": len(sources),
                "sources": list(sources),
                "index_path": self.index_path
            }
            
        except Exception as e:
            return {"error": f"Error getting statistics: {e}"}
    
    def search_documents(self, query: str, doc_type: str = None) -> List[Dict[str, Any]]:
        """Search for specific documents in the knowledge base"""
        
        if not self.retriever:
            return []
        
        try:
            # Retrieve relevant nodes
            nodes = self.retriever.retrieve(query)
            
            results = []
            for node in nodes:
                if hasattr(node, 'metadata'):
                    metadata = node.metadata
                    
                    # Filter by document type if specified
                    if doc_type and metadata.get('doc_type') != doc_type:
                        continue
                    
                    result = {
                        "text": node.text[:200] + "..." if len(node.text) > 200 else node.text,
                        "source": metadata.get('source', 'Unknown'),
                        "doc_type": metadata.get('doc_type', 'Unknown'),
                        "relevance_score": getattr(node, 'score', 0.0)
                    }
                    results.append(result)
            
            return results
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []