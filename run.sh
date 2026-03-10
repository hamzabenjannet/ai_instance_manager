#!/bin/bash

source /home/headless/conda/etc/profile.d/conda.sh

# source activate ai_instance_manager
# OR
conda activate ai_instance_manager

uvicorn main:app --reload --host "0.0.0.0" --port 42014