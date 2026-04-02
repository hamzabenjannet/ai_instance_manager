#!/bin/bash

source /home/headless/conda/etc/profile.d/conda.sh


cd "$(dirname "$0")"

echo "--- current dir:"
pwd

conda activate ai_instance_manager

export HF_TOKEN=hf_...

# Phase 1 only (when you just need the icon detection model)
# python3 download_models_and_weights.py --detect-only

# Everything (when you're ready for Florence-2 captioning)
python3 download_models_and_weights.py