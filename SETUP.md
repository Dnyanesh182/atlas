# ATLAS - Development Setup Guide

## Prerequisites

- Python 3.11 or higher
- pip (Python package installer)
- Virtual environment tool
- OpenAI or Anthropic API key

## Installation Steps

### 1. Clone Repository

```bash
git clone https://github.com/Dnyanesh182/atlas.git
cd atlas
```

### 2. Create Virtual Environment

**On macOS/Linux:**
```bash
python3.11 -m venv venv
source venv/bin/activate
```

**On Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
# Required: Add your API keys
```

Edit `.env`:
```env
OPENAI_API_KEY=sk-your-key-here
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
```

### 5. Create Data Directories

```bash
mkdir -p data/memory
mkdir -p data/traces
mkdir -p logs
```

### 6. Verify Installation

```bash
python quick_start.py
```

If successful, you should see:
```
✅ System initialized
✅ Task created
✅ Task completed
🎉 Success! ATLAS is working correctly.
```

## Troubleshooting

### Issue: Import errors

**Solution:**
```bash
# Ensure you're in the virtual environment
which python  # Should show venv path

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Issue: API key errors

**Solution:**
```bash
# Verify .env file exists and has correct keys
cat .env | grep API_KEY

# Ensure .env is in project root
ls -la .env
```

### Issue: Memory/vector store errors

**Solution:**
```bash
# Install FAISS properly
pip uninstall faiss-cpu
pip install faiss-cpu

# Or use Chroma instead
pip install chromadb
```

## Development Tools

### Install Development Dependencies

```bash
pip install pytest pytest-asyncio black mypy ruff
```

### Run Tests

```bash
pytest tests/ -v
```

### Format Code

```bash
black atlas/
```

### Type Checking

```bash
mypy atlas/
```

## Next Steps

1. **Try Examples**: Run example scripts in `examples/` directory
2. **Start API**: `python examples/04_api_server.py`
3. **Read Docs**: See `README.md` and `docs/` folder
4. **Customize**: Edit `atlas/config.py` for your needs
