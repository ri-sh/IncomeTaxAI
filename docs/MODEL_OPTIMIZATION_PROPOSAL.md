# Model Optimization Proposal for Income Tax AI

## 🎯 Current State Analysis

### Current Model: Llama3:8B
- **Size**: 8 billion parameters (~4.7GB download)
- **Memory Usage**: 6-8GB RAM during inference
- **Performance**: High accuracy but resource-intensive
- **Speed**: ~5-15 seconds per document analysis

### Current Architecture Bottlenecks
1. **High Memory Consumption**: 8GB+ RAM for model inference
2. **Single Model for All Tasks**: One model handles classification + extraction
3. **No Model Caching**: Each request loads full model context
4. **Sequential Processing**: Documents processed one at a time
5. **Large Context Window**: 8192 tokens (often unnecessary)

## 🚀 Proposed Optimization Strategy

### Option 1: Multi-Tier Model Architecture (Recommended)

#### Tier 1: Lightweight Classification Model
**Purpose**: Fast document type identification
- **Model**: `llama3.2:1b` or `gemma2:2b`
- **Size**: 1-2GB (vs 4.7GB)
- **Memory**: 2-3GB RAM
- **Speed**: 1-2 seconds
- **Accuracy**: 95%+ for document classification

#### Tier 2: Specialized Extraction Models
**Purpose**: Targeted data extraction per document type
- **Form16 Model**: Fine-tuned `phi3:mini` (3.8B → 2.7GB)
- **Bank/Investment Model**: `qwen2:1.5b` (1.5B → 0.9GB)
- **General Documents**: `llama3.2:3b` (3B → 2GB)

#### Benefits:
- **70% Memory Reduction**: 2-4GB vs 6-8GB
- **3x Faster**: Parallel processing + smaller models
- **Better Accuracy**: Specialized models per task
- **Scalable**: Add new document types easily

### Option 2: Single Optimized Model

#### Recommended Model: `qwen2.5:7b`
- **Size**: 4.4GB (vs 4.7GB Llama3:8b)
- **Memory**: 4-5GB RAM (vs 6-8GB)
- **Performance**: 15-20% faster inference
- **Accuracy**: Similar or better for structured data
- **Languages**: Better multilingual support

#### Alternative: `llama3.2:3b`
- **Size**: 2GB (58% smaller)
- **Memory**: 3-4GB RAM (50% reduction)
- **Performance**: 2-3x faster
- **Accuracy**: 90-95% (slight reduction)
- **Best for**: Resource-constrained environments

## 📊 Performance Comparison Matrix

| Model | Size | RAM | Speed | Accuracy | Cost |
|-------|------|-----|-------|----------|------|
| **Current: llama3:8b** | 4.7GB | 6-8GB | 1x | 98% | High |
| **qwen2.5:7b** | 4.4GB | 4-5GB | 1.2x | 98% | Medium |
| **llama3.2:3b** | 2.0GB | 3-4GB | 2.5x | 95% | Low |
| **Multi-tier** | 2-4GB | 2-4GB | 3x | 99% | Medium |

## 🛠 Implementation Roadmap

### Phase 1: Quick Win (1-2 days)
1. **Test Alternative Models**
   ```bash
   ollama pull qwen2.5:7b
   ollama pull llama3.2:3b
   ```
2. **Benchmark Performance** on existing test documents
3. **Update Configuration** for best performing model

### Phase 2: Multi-Tier Architecture (1 week)
1. **Document Classification Pipeline**
   - Implement `llama3.2:1b` for fast classification
   - Route to specialized models based on type
2. **Specialized Extractors**
   - Form16: `phi3:mini` with custom prompts
   - Financial: `qwen2:1.5b` for numbers/dates
   - Fallback: `llama3.2:3b` for edge cases
3. **Parallel Processing**
   - Process multiple documents simultaneously
   - Cache model instances for reuse

### Phase 3: Advanced Optimizations (2 weeks)
1. **Model Quantization**
   - Use GGUF Q4_K_M quantization (50% size reduction)
   - Minimal accuracy loss (1-2%)
2. **Context Window Optimization**
   - Dynamic context sizing (2K-8K based on document)
   - Reduce memory usage by 30-50%
3. **Intelligent Fallbacks**
   - Regex extraction for structured fields
   - Model ensembling for critical data

## 💡 Specific Model Recommendations

### For Different Use Cases:

#### 🏎 Maximum Speed (Resource Constrained)
```bash
Primary: llama3.2:1b    # Classification (0.7GB)
Fallback: qwen2:1.5b    # Extraction (0.9GB)
Total RAM: ~2GB
Speed: 3-5x faster
```

#### ⚖️ Balanced Performance (Recommended)
```bash
Primary: qwen2.5:7b     # All tasks (4.4GB)
Memory: 4-5GB
Speed: 1.2x faster
Accuracy: 98%
```

#### 🎯 Maximum Accuracy
```bash
Classification: llama3.2:3b  # Fast routing (2GB)
Form16: phi3:mini           # Specialized (2.7GB)
Financial: qwen2.5:7b       # Numbers expert (4.4GB)
Total: Multi-model approach with model swapping
```

## 🔧 Technical Implementation

### 1. Model Configuration Updates
```python
# src/core/document_processing/model_config.py
MODEL_CONFIGS = {
    "lightweight": {
        "classification": "llama3.2:1b",
        "extraction": "qwen2:1.5b",
        "memory_limit": "3GB"
    },
    "balanced": {
        "primary": "qwen2.5:7b",
        "memory_limit": "5GB"
    },
    "accurate": {
        "classification": "llama3.2:3b",
        "form16": "phi3:mini",
        "financial": "qwen2.5:7b"
    }
}
```

### 2. Environment Configuration
```bash
# .env additions
MODEL_TIER=balanced  # lightweight|balanced|accurate
CLASSIFICATION_MODEL=qwen2.5:7b
EXTRACTION_MODEL=qwen2.5:7b
MAX_MEMORY_GB=5
CONTEXT_WINDOW=4096
```

### 3. Docker Resource Limits
```yaml
# docker-compose.cpu.yml updates
services:
  celery:
    deploy:
      resources:
        limits:
          memory: 5G  # Reduced from 8G
        reservations:
          memory: 3G  # Reduced from 6G
```

## 📈 Expected Improvements

### Resource Usage
- **Memory**: 50-70% reduction (3-5GB vs 6-8GB)
- **Storage**: 30-60% reduction (2-4GB vs 4.7GB)
- **CPU**: 20-40% reduction due to faster inference

### Performance
- **Speed**: 2-3x faster document processing
- **Throughput**: Handle 3-5x more documents simultaneously
- **Scalability**: Deploy on 4GB RAM machines

### User Experience
- **Faster Results**: 3-7 seconds vs 10-20 seconds
- **Better Resource Sharing**: Multiple users without slowdown
- **Mobile Friendly**: Lower resource requirements

## 🎛 Migration Strategy

### Immediate (This Week)
1. **Test qwen2.5:7b** as drop-in replacement
2. **Benchmark accuracy** on test documents
3. **Update documentation** with new requirements

### Short Term (Next 2 Weeks)
1. **Implement model selection** via environment variables
2. **Add performance monitoring** for resource usage
3. **Create fallback mechanisms** for model failures

### Long Term (Next Month)
1. **Multi-tier architecture** with specialized models
2. **Auto-scaling** based on document volume
3. **Model fine-tuning** on domain-specific data

## 🔍 Risk Assessment

### Low Risk Changes
- ✅ Single model replacement (qwen2.5:7b)
- ✅ Environment-based model selection
- ✅ Resource limit adjustments

### Medium Risk Changes
- ⚠️ Multi-model architecture (requires testing)
- ⚠️ Parallel processing changes
- ⚠️ Context window optimization

### High Risk Changes
- 🔴 Model quantization (accuracy impact)
- 🔴 Custom model fine-tuning
- 🔴 Major architecture changes

## 🎯 Recommended Next Steps

1. **Immediate Action**: Test `qwen2.5:7b` as drop-in replacement
2. **Quick Wins**: Implement environment-based model selection
3. **Gradual Migration**: Multi-tier architecture over 2-3 weeks
4. **Continuous Monitoring**: Track performance metrics throughout

This proposal balances performance improvements with implementation complexity, providing multiple paths forward based on your priorities and constraints.