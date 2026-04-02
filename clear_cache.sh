#!/bin/bash

# =============================================================================
# clear_cache.sh — Clean up all cached/generated files for a fresh run
# =============================================================================
# Usage:
#   ./clear_cache.sh              # clear outputs + HuggingFace modules cache
#   ./clear_cache.sh --weights    # also delete downloaded model weights
#   ./clear_cache.sh --all        # everything above + full HuggingFace hub cache
# =============================================================================
source /home/headless/conda/etc/profile.d/conda.sh

conda activate ai_instance_manager

cd "$(dirname "$0")"

echo "--- current dir:"
pwd

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Flags
CLEAR_WEIGHTS=false
CLEAR_HF_HUB=false

for arg in "$@"; do
    case $arg in
        --weights) CLEAR_WEIGHTS=true ;;
        --all)     CLEAR_WEIGHTS=true; CLEAR_HF_HUB=true ;;
    esac
done

echo "=============================="
echo " AI Instance Manager — Clear Cache"
echo "=============================="

# --- Output directories ---
echo ""
echo "[outputs] Clearing screenshots, annotated images, and JSON outputs..."

find "$SCRIPT_DIR/output/screenshots" -name "*.png" -delete 2>/dev/null && \
    echo "  [done] output/screenshots/*.png" || echo "  [skip] output/screenshots (empty or missing)"

find "$SCRIPT_DIR/output/annotated" -name "*.png" -delete 2>/dev/null && \
    echo "  [done] output/annotated/*.png" || echo "  [skip] output/annotated (empty or missing)"

find "$SCRIPT_DIR/output/json" -name "*.json" -delete 2>/dev/null && \
    echo "  [done] output/json/*.json" || echo "  [skip] output/json (empty or missing)"

# --- Python __pycache__ ---
echo ""
echo "[pycache] Removing __pycache__ directories..."
find "$SCRIPT_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null && \
    echo "  [done] all __pycache__ removed" || echo "  [skip] no __pycache__ found"

# --- HuggingFace modules cache (Florence-2 custom code) ---
echo ""
echo "[hf-modules] Clearing HuggingFace transformers_modules cache..."
HF_MODULES_DIR="$HOME/.cache/huggingface/modules/transformers_modules"
if [ -d "$HF_MODULES_DIR" ]; then
    rm -rf "$HF_MODULES_DIR"
    echo "  [done] $HF_MODULES_DIR"
else
    echo "  [skip] $HF_MODULES_DIR (not found)"
fi

# --- Model weights (optional) ---
if [ "$CLEAR_WEIGHTS" = true ]; then
    echo ""
    echo "[weights] Removing downloaded model weights..."
    if [ -d "$SCRIPT_DIR/weights" ]; then
        rm -rf "$SCRIPT_DIR/weights"
        echo "  [done] weights/ deleted — re-run download_models_and_weights.py to restore"
    else
        echo "  [skip] weights/ not found"
    fi
fi

# --- Full HuggingFace hub cache (optional) ---
if [ "$CLEAR_HF_HUB" = true ]; then
    echo ""
    echo "[hf-hub] Clearing full HuggingFace hub cache..."
    HF_HUB_DIR="$HOME/.cache/huggingface/hub"
    if [ -d "$HF_HUB_DIR" ]; then
        rm -rf "$HF_HUB_DIR"
        echo "  [done] $HF_HUB_DIR"
    else
        echo "  [skip] $HF_HUB_DIR (not found)"
    fi
fi

echo ""
echo "=============================="
echo " Done."
echo "=============================="