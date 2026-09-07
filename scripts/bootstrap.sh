#!/bin/bash
# Bootstrap script for macOS - Initialize canvasxpress-examples-jupyter workspace
set -e

echo "================================================"
echo " CanvasXpress Examples Jupyter - Setup"
echo "================================================"
echo ""

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "ERROR: uv not found. Please install uv first:"
    echo "  pip install uv"
    echo "  OR follow instructions at https://github.com/astral-sh/uv"
    exit 1
fi

echo "[1/3] Checking Python version..."
uv python install 3.12

echo "[2/3] Installing dependencies with uv..."
uv sync

echo "[3/3] Installing Jupyter kernel..."
uv run python -m ipykernel install --user --name canvasxpress-examples --display-name "Python 3.12 (CanvasXpress Examples)"

echo ""
echo "================================================"
echo " Setup Complete!"
echo "================================================"
echo ""
echo "To start JupyterLab:"
echo "  uv run jupyter lab"
echo ""
echo "To start Jupyter Notebook:"
echo "  uv run jupyter notebook"
echo ""
echo "Examples are in the examples/ directory"
echo ""
