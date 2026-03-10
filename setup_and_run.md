# Install Dependencies and run the project

```bash
#!/bin/bash
conda create -n ai_instance_manager python=3.11 -c conda-forge -y
source activate ai_instance_manager
# OR
conda activate ai_instance_manager
# pip install <NEEDED_MODULES>
pip install fastapi uvicorn
# pip freeze > requirements.txt

pip install --upgrade Pillow

sudo apt install gnome-screenshot -y

pip list --format=freeze | grep -v "@ file://" > requirements.txt
# install from requirements.txt
pip install -r requirements.txt

# start the app
uvicorn main:app --reload --host 0.0.0.0 --port 42014
# OR
bash ./run.sh
```
