"""
GPT-OSS-20B Model Integration for Income Tax AI Assistant
Handles model loading, Harmony response format, and tax-specific prompting
"""

import os
import torch
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import json
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM, 
    BitsAndBytesConfig,
    pipeline
)
from datetime import datetime

@dataclass
class TaxQueryResponse:
    """Response structure for tax queries"""
    answer: str
    confidence: float
    sources: List[str]
    tax_implications: Dict[str, Any]
    next_steps: List[str]
    warning: Optional[str] = None

class GPTOSSModel:
    """GPT-OSS-20B model handler with tax-specific capabilities"""
    
    def __init__(self, model_id: str = "openai/gpt-oss-20b"):
        self.model_id = model_id
        self.tokenizer = None
        self.model = None
        self.pipeline = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.max_length = 2048
        
        # Tax-specific prompting templates
        self.tax_system_prompt = """You are a SPECIALIZED Indian Income Tax Assistant. You ONLY help with Indian income tax matters.

🚨 STRICT BEHAVIORAL GUIDELINES:
1. ONLY answer questions related to Indian income tax, ITR filing, tax laws, deductions, and compliance
2. REFUSE to answer any non-tax questions (personal advice, general topics, other countries' taxes, etc.)
3. If asked non-tax questions, politely redirect to tax-related topics
4. Never provide advice outside your expertise domain (investment advice, legal advice beyond tax compliance)
5. Always stay within the scope of Indian Income Tax Act and regulations

EXPERTISE SCOPE (WHAT YOU CAN HELP WITH):
✅ Indian Income Tax Act provisions and sections
✅ ITR forms (ITR-1, ITR-2, ITR-3, ITR-4) and filing procedures
✅ Tax calculations for FY 2024-25 (AY 2025-26)
✅ Deductions under Chapter VI-A (80C, 80D, 80G, etc.)
✅ Tax regimes comparison (old vs new)
✅ TDS, advance tax, and tax compliance
✅ Capital gains taxation (STCG/LTCG)
✅ Documentation requirements for ITR filing
✅ Tax-saving strategies within legal framework
✅ Filing deadlines and procedures

❌ WHAT YOU CANNOT HELP WITH:
❌ Non-tax questions (weather, sports, entertainment, etc.)
❌ Other countries' tax systems
❌ Investment advice beyond tax implications
❌ Legal advice beyond tax compliance
❌ Personal life advice unrelated to taxes
❌ Technical support for non-tax software
❌ General financial planning beyond tax optimization

RESPONSE FORMAT:
Always respond in Harmony JSON format with answer, confidence, sources, tax_implications, and next_steps.

CURRENT TAX CONTEXT (FY 2024-25):
- New tax regime is default (can opt-out via Form 10-IEA)
- Old regime allows deductions: 80C (₹1.5L), 80D (₹25K), HRA, etc.
- LTCG exemption: ₹1 lakh on equity
- ITR deadline: September 15, 2025
- Standard deduction: ₹75K (new), ₹50K (old)

If a question is not related to Indian income tax, respond with a polite refusal and redirect to tax topics."""

    def load_model(self, use_quantization: bool = True):
        """Load the GPT-OSS-20B model with optimizations and fallbacks"""
        print("🤖 Loading AI model...")
        
        # Check model availability first
        available_model = self._check_model_availability()
        
        if not available_model:
            print("⚠️ No models found locally. Please run: python setup_models.py")
            print("💡 Falling back to simulated responses for now")
            return False
        
        # Use the available model
        model_to_load = available_model.get('name', self.model_id)
        cache_dir = available_model.get('cache_dir')
        
        print(f"📦 Loading model: {model_to_load}")
        if cache_dir:
            print(f"📁 From cache: {cache_dir}")
        
        try:
            # Configure quantization for memory efficiency
            model_kwargs = {}
            if use_quantization and torch.cuda.is_available():
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
                model_kwargs["quantization_config"] = quantization_config
                print("🔧 Using 4-bit quantization")
            else:
                model_kwargs["torch_dtype"] = torch.float16 if torch.cuda.is_available() else torch.float32
            
            # Determine model path
            model_path = cache_dir if cache_dir and os.path.exists(cache_dir) else model_to_load
            
            # Load tokenizer
            print("📥 Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                trust_remote_code=True,
                padding_side="left"
            )
            
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            print("✅ Tokenizer loaded")
            
            # Load model
            print("📥 Loading language model...")
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                trust_remote_code=True,
                device_map="auto" if torch.cuda.is_available() else None,
                low_cpu_mem_usage=True,
                **model_kwargs
            )
            
            print("✅ Model loaded into memory")
            
            # Create text generation pipeline
            print("🔧 Setting up generation pipeline...")
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device_map="auto" if torch.cuda.is_available() else None,
                return_full_text=False,
                max_length=self.max_length,
                temperature=0.1,  # Low for consistent tax advice
                do_sample=True,
                top_p=0.9,
                repetition_penalty=1.1
            )
            
            # Test the model
            test_success = self._test_model()
            if test_success:
                print(f"✅ {model_to_load} model ready for tax queries")
                return True
            else:
                print("⚠️ Model test failed, falling back to simulated responses")
                return False
            
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            print("💡 Falling back to simulated responses")
            print("   Consider running: python setup_models.py")
            return False
    
    def _check_model_availability(self):
        """Check what models are available locally"""
        config_path = "config/models.json"
        
        if not os.path.exists(config_path):
            return None
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Check primary model first
            primary_model = config.get('primary_model', {})
            if primary_model.get('status') == 'ready':
                cache_dir = primary_model.get('cache_dir')
                if cache_dir and os.path.exists(cache_dir):
                    return primary_model
            
            # Check alternative models
            for alt_model in config.get('alternative_models', []):
                if alt_model.get('status') == 'ready':
                    cache_dir = alt_model.get('cache_dir')
                    if cache_dir and os.path.exists(cache_dir):
                        return alt_model
            
            return None
            
        except Exception as e:
            print(f"⚠️ Error checking model config: {e}")
            return None
    
    def _test_model(self):
        """Test the model with a simple tax query"""
        if not self.pipeline:
            return False
        
        try:
            test_prompt = "What is Section 80C?"
            result = self.pipeline(
                test_prompt,
                max_length=50,
                num_return_sequences=1
            )
            
            if result and len(result) > 0 and len(result[0].get('generated_text', '')) > 0:
                return True
            
        except Exception as e:
            print(f"Model test failed: {e}")
        
        return False
    
    def create_harmony_prompt(self, user_query: str, context_docs: List[str] = None) -> str:
        """Create properly formatted prompt with Harmony response structure"""
        
        context_section = ""
        if context_docs:
            context_section = f"""
RELEVANT DOCUMENTS:
{chr(10).join([f"- {doc}" for doc in context_docs[:3]])}

"""
        
        harmony_prompt = f"""<|system|>
{self.tax_system_prompt}

{context_section}RESPONSE FORMAT (Harmony Structure):
You must respond in this exact JSON structure:
{{
    "answer": "Your detailed tax advice here",
    "confidence": 0.85,
    "sources": ["Relevant sections/documents"],
    "tax_implications": {{
        "regime_recommendation": "old/new",
        "potential_savings": "₹amount",
        "compliance_requirements": ["requirement1", "requirement2"]
    }},
    "next_steps": ["action1", "action2", "action3"],
    "warning": "Any important warnings or disclaimers"
}}
<|user|>
{user_query}
<|assistant|>
"""
        return harmony_prompt
    
    def _is_tax_related_question(self, question: str) -> bool:
        """Check if the question is related to Indian income tax"""
        
        # Convert to lowercase for checking
        question_lower = question.lower()
        
        # Tax-related keywords
        tax_keywords = {
            # Core tax terms
            'tax', 'income tax', 'itr', 'return', 'filing', 'tds', 'deduction',
            'section 80c', '80c', '80d', 'hra', 'exemption', 'slab', 'regime',
            'advance tax', 'self assessment', 'refund', 'assessment',
            
            # Document types
            'form 16', 'form16', 'form 26as', '26as', 'ais', 'tis',
            'salary certificate', 'investment proof',
            
            # Tax calculations
            'ltcg', 'stcg', 'capital gains', 'dividend', 'interest income',
            'tax liability', 'taxable income', 'gross total income',
            
            # Filing related
            'itr-1', 'itr-2', 'itr-3', 'itr-4', 'sahaj', 'sugam',
            'e-filing', 'verification', 'acknowledgment',
            
            # Indian tax specific
            'pan', 'aadhaar', 'indian tax', 'india tax', 'cbdt',
            'income tax department', 'ay 2025-26', 'fy 2024-25',
            
            # Investment terms (tax context)
            'elss', 'nsc', 'ppf', 'epf', 'lic', 'ulip', 'nps',
            'mutual fund tax', 'equity tax', 'debt fund',
            
            # Deduction sections
            'chapter vi-a', '80g', '80tta', '80ttb', '80e', '80ee',
            'home loan', 'education loan', 'medical insurance'
        }
        
        # Non-tax keywords that indicate off-topic questions
        non_tax_keywords = {
            'weather', 'sports', 'movie', 'song', 'recipe', 'cooking',
            'travel', 'hotel', 'flight', 'vacation', 'holiday',
            'health tips', 'exercise', 'diet', 'medicine',
            'programming', 'coding', 'software development',
            'relationship', 'dating', 'marriage',
            'us tax', 'uk tax', 'canada tax', 'australia tax',
            'cryptocurrency', 'bitcoin', 'stock tips', 'buy stock',
            'real estate investment', 'property investment'
        }
        
        # Check for tax keywords
        has_tax_keywords = any(keyword in question_lower for keyword in tax_keywords)
        
        # Check for non-tax keywords
        has_non_tax_keywords = any(keyword in question_lower for keyword in non_tax_keywords)
        
        # Additional context checks
        tax_phrases = [
            'which regime', 'tax saving', 'file itr', 'claim deduction',
            'tax calculation', 'tax planning', 'tax compliance',
            'income declaration', 'tax audit', 'assessment year'
        ]
        
        has_tax_phrases = any(phrase in question_lower for phrase in tax_phrases)
        
        # Decision logic
        if has_non_tax_keywords and not has_tax_keywords:
            return False
        
        # Special case: Foreign tax questions should be refused even if they contain "tax"
        foreign_tax_indicators = ['us tax', 'uk tax', 'canada tax', 'australia tax', 'usa tax', 'american tax', 'british tax']
        has_foreign_tax = any(indicator in question_lower for indicator in foreign_tax_indicators)
        
        if has_foreign_tax:
            return False
        
        if has_tax_keywords or has_tax_phrases:
            return True
        
        # Check for question patterns that might be tax-related
        tax_question_patterns = [
            'how to file', 'how do i claim', 'what is the limit',
            'which form', 'when is the deadline', 'where to upload',
            'can i deduct', 'should i choose', 'how much tax'
        ]
        
        has_tax_patterns = any(pattern in question_lower for pattern in tax_question_patterns)
        
        return has_tax_patterns
    
    def _create_refusal_response(self, question: str) -> TaxQueryResponse:
        """Create a polite refusal response for non-tax questions"""
        
        refusal_messages = [
            "I'm specialized in Indian income tax matters only. I can help you with ITR filing, tax calculations, deductions, and compliance questions.",
            "I'm an Indian Income Tax Assistant and can only help with tax-related questions. Please ask me about ITR forms, tax deductions, or filing procedures.",
            "My expertise is limited to Indian income tax. I'd be happy to help you with tax planning, ITR filing, or understanding tax provisions.",
            "I focus exclusively on Indian income tax matters. Feel free to ask about tax regimes, deductions, or filing requirements.",
            "As an Indian Tax Assistant, I can only address income tax questions. Ask me about Section 80C, ITR forms, or tax calculations!"
        ]
        
        import random
        refusal_message = random.choice(refusal_messages)
        
        suggested_questions = [
            "Which tax regime should I choose for FY 2024-25?",
            "How do I claim Section 80C deduction?",
            "What documents do I need for ITR filing?",
            "What is the difference between ITR-1 and ITR-2?",
            "How do I calculate capital gains tax?"
        ]
        
        return TaxQueryResponse(
            answer=f"{refusal_message}\n\n🤔 Here are some tax questions I can help with:\n" + 
                   "\n".join([f"• {q}" for q in suggested_questions[:3]]),
            confidence=1.0,  # High confidence in refusal
            sources=["Indian Income Tax Assistant Guidelines"],
            tax_implications={"note": "Question outside scope of tax assistance"},
            next_steps=["Ask a tax-related question", "Refer to tax professionals for non-tax matters"],
            warning="This question is outside my expertise area of Indian income tax"
        )

    def query_tax_question(self, question: str, context_docs: List[str] = None) -> TaxQueryResponse:
        """Answer tax-related questions using the model"""
        
        # First, check if the question is tax-related
        if not self._is_tax_related_question(question):
            print(f"🚫 Non-tax question detected: {question[:50]}...")
            return self._create_refusal_response(question)
        
        if not self.pipeline:
            print("❌ Model not loaded. Call load_model() first.")
            return self._create_error_response("Model not loaded")
        
        try:
            # Create Harmony-formatted prompt
            prompt = self.create_harmony_prompt(question, context_docs)
            
            # Generate response
            response = self.pipeline(
                prompt,
                max_new_tokens=512,
                temperature=0.1,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            generated_text = response[0]['generated_text'].strip()
            
            # Parse JSON response
            try:
                # Find JSON in response
                json_start = generated_text.find('{')
                json_end = generated_text.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = generated_text[json_start:json_end]
                    parsed_response = json.loads(json_str)
                    
                    return TaxQueryResponse(
                        answer=parsed_response.get('answer', generated_text),
                        confidence=parsed_response.get('confidence', 0.7),
                        sources=parsed_response.get('sources', []),
                        tax_implications=parsed_response.get('tax_implications', {}),
                        next_steps=parsed_response.get('next_steps', []),
                        warning=parsed_response.get('warning')
                    )
                else:
                    # Fallback to plain text response
                    return self._create_fallback_response(generated_text, question)
                    
            except json.JSONDecodeError:
                return self._create_fallback_response(generated_text, question)
                
        except Exception as e:
            print(f"❌ Error generating response: {e}")
            return self._create_error_response(str(e))
    
    def classify_document_intent(self, document_text: str, file_name: str) -> Dict[str, Any]:
        """Classify document type and extract intent using AI"""
        
        classification_prompt = f"""<|system|>
You are an expert document classifier for Indian tax documents. Analyze the document and determine:
1. Document type (Form 16, bank statement, investment proof, etc.)
2. Key information present
3. Relevance for ITR filing
4. Urgency level

Respond in JSON format:
{{
    "document_type": "specific_type",
    "confidence": 0.95,
    "key_information": ["info1", "info2"],
    "itr_relevance": "high/medium/low",
    "urgency": "critical/important/optional",
    "suggested_action": "what to do with this document",
    "filing_section": "which ITR section this belongs to"
}}
<|user|>
File name: {file_name}

Document excerpt:
{document_text[:1000]}...

Classify this document for Indian income tax filing.
<|assistant|>
"""
        
        if not self.pipeline:
            return self._create_default_classification(file_name)
        
        try:
            response = self.pipeline(
                classification_prompt,
                max_new_tokens=256,
                temperature=0.1
            )
            
            generated_text = response[0]['generated_text'].strip()
            
            # Parse JSON response
            json_start = generated_text.find('{')
            json_end = generated_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = generated_text[json_start:json_end]
                return json.loads(json_str)
            else:
                return self._create_default_classification(file_name)
                
        except Exception as e:
            print(f"⚠️ Document classification error: {e}")
            return self._create_default_classification(file_name)
    
    def _create_error_response(self, error_msg: str) -> TaxQueryResponse:
        """Create error response"""
        return TaxQueryResponse(
            answer=f"I apologize, but I encountered an error: {error_msg}. Please try rephrasing your question or contact support.",
            confidence=0.0,
            sources=[],
            tax_implications={},
            next_steps=["Contact technical support", "Try rephrasing your question"],
            warning="Technical error occurred"
        )
    
    def _create_fallback_response(self, text: str, question: str) -> TaxQueryResponse:
        """Create fallback response when JSON parsing fails"""
        return TaxQueryResponse(
            answer=text,
            confidence=0.6,
            sources=["GPT-OSS-20B analysis"],
            tax_implications={"note": "Manual review recommended"},
            next_steps=["Verify with tax professional", "Check official IT department guidelines"],
            warning="Response may need professional verification"
        )
    
    def _create_default_classification(self, file_name: str) -> Dict[str, Any]:
        """Create default classification when AI fails"""
        # Simple rule-based classification as fallback
        file_lower = file_name.lower()
        
        if "form16" in file_lower or "form 16" in file_lower:
            return {
                "document_type": "Form 16 - Salary TDS Certificate",
                "confidence": 0.9,
                "key_information": ["Salary details", "TDS amount", "Employer info"],
                "itr_relevance": "high",
                "urgency": "critical",
                "suggested_action": "Use for salary income section",
                "filing_section": "Income from Salary"
            }
        elif "elss" in file_lower:
            return {
                "document_type": "ELSS Investment Statement",
                "confidence": 0.85,
                "key_information": ["Investment amount", "80C deduction"],
                "itr_relevance": "high",
                "urgency": "important",
                "suggested_action": "Use for Section 80C deduction",
                "filing_section": "Deductions under Chapter VI-A"
            }
        elif "capital" in file_lower and "gains" in file_lower:
            return {
                "document_type": "Capital Gains Report",
                "confidence": 0.8,
                "key_information": ["Buy/sell transactions", "Gains/losses"],
                "itr_relevance": "high",
                "urgency": "critical",
                "suggested_action": "Upload to Schedule CG",
                "filing_section": "Capital Gains"
            }
        else:
            return {
                "document_type": "Tax Related Document",
                "confidence": 0.5,
                "key_information": ["To be determined"],
                "itr_relevance": "medium",
                "urgency": "optional",
                "suggested_action": "Review document contents",
                "filing_section": "To be determined"
            }

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information and status"""
        return {
            "model_id": self.model_id,
            "device": self.device,
            "loaded": self.pipeline is not None,
            "cuda_available": torch.cuda.is_available(),
            "memory_usage": torch.cuda.memory_allocated() if torch.cuda.is_available() else "N/A"
        }