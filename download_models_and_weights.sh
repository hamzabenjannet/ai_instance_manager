#!/bin/bash

mkdir -p weights

for f in icon_detect/model.pt icon_detect/model.yaml icon_detect/train_args.yaml; do
  huggingface-cli download microsoft/OmniParser-v2.0 "$f" --local-dir weights
done

for f in icon_caption/config.json icon_caption/generation_config.json icon_caption/model.safetensors; do
  huggingface-cli download microsoft/OmniParser-v2.0 "$f" --local-dir weights
done

mv weights/icon_caption weights/icon_caption_florence