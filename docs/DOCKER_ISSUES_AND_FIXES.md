# Docker Deployment Issues and Fixes

## Issue Summary
During Docker deployment of the Income Tax AI application, several critical performance issues were identified that caused Celery workers to hang and documents to remain stuck in processing state.

## Root Cause Analysis

### Native vs Docker Environment Comparison

| Aspect | Native Setup (Working) | Docker Setup (Issues) | Impact |
|--------|------------------------|------------------------|---------|
| **Memory Mapping** | Enabled (default) | Disabled (`--no-mmap`) | High CPU, slower access |
| **OS Environment** | macOS native | Ubuntu container on macOS | Resource isolation overhead |
| **Hardware Access** | Direct | Virtualized through Docker | Reduced efficiency |
| **Resource Management** | OS-optimized | Container-limited | Memory pressure |
| **Network** | localhost | Docker network | Additional latency |

### Detailed Technical Findings

#### 1. Ollama Memory Mapping Issue
**Problem**: Docker Ollama runs with `--no-mmap` flag, forcing entire model into RAM
```bash
# Docker process (problematic)
/usr/bin/ollama runner --model ... --no-mmap --parallel 1

# Native process would use memory mapping for efficiency
```

**Impact**: 
- 1200%+ CPU usage during inference
- Workers hanging on API calls for 30+ minutes
- Memory pressure causing instability

#### 2. Resource Allocation Problems
**Problem**: Initial Docker configuration insufficient for AI workloads
```yaml
# Before (insufficient)
CELERY_TASK_TIME_LIMIT = 600      # 10 minutes
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 500000  # 500MB

# After (appropriate for AI)
CELERY_TASK_TIME_LIMIT = 2400     # 40 minutes  
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 2000000 # 2GB
```

#### 3. Concurrent Request Overload
**Problem**: Multiple workers simultaneously hitting Ollama
- 3 Celery workers each making concurrent AI requests
- Ollama not configured for concurrent handling
- Resource contention causing hangs

#### 4. PDF Processing Bottleneck
**Problem**: Camelot table extraction processing all pages
```python
# Before (slow)
tables = camelot.read_pdf(str(file_path), pages='all')

# After (optimized)  
tables = camelot.read_pdf(str(file_path), pages='1-5')
```

## Solutions Implemented

### 1. Ollama Configuration Optimization
```yaml
environment:
  - OLLAMA_MMAP=1                    # Enable memory mapping
  - OLLAMA_NUM_PARALLEL=1            # Limit concurrent requests
  - OLLAMA_MAX_LOADED_MODELS=1       # Reduce memory pressure
deploy:
  resources:
    limits:
      memory: 8G                     # Adequate memory allocation
    reservations:
      memory: 6G
```

### 2. Celery Worker Tuning
```yaml
# Increased memory limits per worker
deploy:
  resources:
    limits:
      memory: 4G
    reservations:
      memory: 2G

# Added task restart policy
command: celery -A incometax_project worker --max-tasks-per-child=1
```

### 3. Task Timeout Adjustments
```python
# Settings.py
CELERY_TASK_SOFT_TIME_LIMIT = 1800  # 30 minutes
CELERY_TASK_TIME_LIMIT = 2400       # 40 minutes
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 2000000  # 2GB

# Task decorators
@shared_task(bind=True, time_limit=2400, soft_time_limit=1800)
```

### 4. PDF Processing Optimization
```python
# Limited page processing to prevent hanging
tables = camelot.read_pdf(str(file_path), pages='1-5', flavor='lattice')

# Reduced Ollama context window to match Docker config
context_window=8192    # Match Docker Ollama settings
request_timeout=120.0  # Prevent indefinite hangs
```

### 5. Health Check Implementation
```python
# health_check.py - Comprehensive system diagnostics
- Redis connectivity
- Ollama service status  
- Celery broker health
- Memory usage monitoring
- AI inference testing
```

## Performance Results

### Before Fixes
- **CPU Usage**: 1200%+ during processing
- **Document Processing**: Hung indefinitely
- **Worker Availability**: 2/3 workers stuck
- **Memory Usage**: 87.4% system memory
- **Task Completion**: 0% success rate

### After Fixes  
- **CPU Usage**: 6% idle, 200% during active inference (normal)
- **Document Processing**: Completes successfully
- **Worker Availability**: All 3 workers responsive
- **Memory Usage**: Stable with adequate headroom
- **Task Completion**: Expected success rate

## Monitoring and Debugging Tools

### Real-time Monitoring
```bash
# Container resource usage
docker stats

# Worker status
docker-compose exec celery celery -A incometax_project inspect ping

# Task queue status  
docker-compose exec redis redis-cli llen celery

# Health check
docker-compose exec celery python health_check.py
```

### Log Analysis
```bash
# Ollama performance
docker logs incometax_project-ollama-1

# Worker debugging
docker-compose logs -f celery celery2 celery3

# Flower dashboard
http://localhost:5555
```

## Deployment Best Practices

### 1. Docker Desktop Configuration
- **Memory**: Increase to 12GB (from default ~8GB)
- **CPU**: Ensure all cores available to containers
- **Storage**: Adequate space for model files

### 2. Environment-Specific Compose Files
- **GPU**: `docker-compose.yml` for NVIDIA GPU systems
- **CPU**: `docker-compose.cpu.yml` for CPU-only deployments
- **Auto-detection**: `deploy.sh` script chooses appropriate config

### 3. Resource Planning
```yaml
# Recommended resource allocation for 16GB system
ollama:    8GB (6GB reserved)
celery:    6GB total (2GB per worker)  
web+db:    2GB
system:    2GB available
```

### 4. Scaling Guidelines
- **Single Worker**: Development/testing
- **3 Workers**: Production with adequate monitoring
- **More Workers**: Only with horizontal scaling (multiple machines)

## Lessons Learned

1. **Container Defaults**: Docker container defaults may not be optimal for AI workloads
2. **Memory Mapping**: Critical for large model performance in containers
3. **Resource Isolation**: Can both help and hinder depending on configuration
4. **Monitoring**: Essential for identifying bottlenecks in containerized AI systems
5. **Environment Parity**: Native and container environments require careful tuning for consistency

## Future Improvements

1. **Connection Pooling**: Implement Ollama request queuing
2. **Circuit Breaker**: Add failure detection and recovery
3. **Auto-scaling**: Dynamic worker scaling based on load
4. **Metrics**: Prometheus/Grafana integration for detailed monitoring
5. **Model Optimization**: Consider smaller models for faster processing

---

**Date**: 2025-08-16  
**Environment**: macOS 15.4.1, Docker Desktop, 16GB RAM  
**Application**: Income Tax AI Document Processing System