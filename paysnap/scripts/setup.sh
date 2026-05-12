#!/bin/bash
set -e

echo "======================================"
echo "   PaySnap Setup"
echo "======================================"

echo "Installing Python packages..."
pip install -r requirements.txt

echo "Checking Ollama..."
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.ai/install.sh | sh
fi

if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    ollama serve &
    sleep 3
fi

echo "Downloading Gemma 4 (~3.5GB)..."
ollama pull gemma4

echo "Building database..."
python3 data/build_db.py

echo "Running tests..."
python3 -m pytest tests/ -q

echo ""
echo "Setup complete!"
echo "Run: python app/main.py"
echo "Open: http://localhost:7860"