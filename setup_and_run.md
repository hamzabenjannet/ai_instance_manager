# Install Dependencies and run the project

```bash
#!/bin/bash
conda create -n ai_instance_manager python=3.11 -c conda-forge -y
# source activate ai_instance_manager
# OR
conda activate ai_instance_manager
# pip install <NEEDED_MODULES>
pip install fastapi uvicorn
pip install --upgrade Pillow
pip install ultralytics
pip install opencv-python-headless
pip install transformers timm einops easyocr
pip install "transformers==4.38.2"

# CUDA only
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
# CUDA only

sudo apt install gnome-screenshot -y


pip uninstall -y \
  cuda-bindings \
  cuda-pathfinder \
  nvidia-cublas-cu12 \
  nvidia-cuda-cupti-cu12 \
  nvidia-cuda-nvrtc-cu12 \
  nvidia-cuda-runtime-cu12 \
  nvidia-cudnn-cu12 \
  nvidia-cufft-cu12 \
  nvidia-cufile-cu12 \
  nvidia-curand-cu12 \
  nvidia-cusolver-cu12 \
  nvidia-cusparse-cu12 \
  nvidia-cusparselt-cu12 \
  nvidia-nccl-cu12 \
  nvidia-nvjitlink-cu12 \
  nvidia-nvshmem-cu12 \
  nvidia-nvtx-cu12 \
  triton

pip uninstall -y torch torchvision
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# install from requirements.txt
pip install -r requirements.txt

# pip freeze > requirements.txt
pip list --format=freeze | grep -v "@ file://" > requirements.txt

# start the app
uvicorn main:app --reload --host 0.0.0.0 --port 42014
# OR
bash ./run.sh
```

# Setup SSH key for the MCP server

This should be run once if the root user does not have an SSH key.

```bash
# Inside the VNC container — run once
ssh-keygen -t rsa -b 4096 -f /root/.ssh/id_rsa -N ""
cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
```
