#!/bin/bash
# First-time setup script for Ejicode BDP

set -e

echo "Setting up Ejicode AI Business Development Platform..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed. Please install Docker."
    exit 1
fi

# Copy environment file
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please configure .env with your settings"
fi

# Create necessary directories
mkdir -p data/postgres data/redis data/ollama data/chroma

# Pull Ollama models
echo "This will download Ollama models (~10-20GB)..."
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker pull ollama/ollama:latest
    echo "Run 'docker-compose up ollama' and then:"
    echo "  docker exec ejicode_ollama ollama pull deepseek-r1:8b"
    echo "  docker exec ejicode_ollama ollama pull llama2:7b"
    echo "  docker exec ejicode_ollama ollama pull mistral:7b"
    echo "  docker exec ejicode_ollama ollama pull qwen2.5-coder:7b"
    echo "  docker exec ejicode_ollama ollama pull nomic-embed-text:latest"
fi

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Configure .env"
echo "2. Run: docker-compose up -d"
echo "3. Run: docker-compose exec backend alembic upgrade head"
echo "4. Access: http://localhost:8000 (API), http://localhost:3000 (Frontend)"
