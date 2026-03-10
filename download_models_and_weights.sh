#!/bin/bash

export HF_TOKEN=hf_...

# Phase 1 only (when you just need the icon detection model)
# python3 download_models_and_weights.py --detect-only

# Everything (when you're ready for Florence-2 captioning)
python3 download_models_and_weights.py