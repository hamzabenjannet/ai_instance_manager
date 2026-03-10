#!/bin/bash

source activate ai_instance_manager

uvicorn main:app --reload --host "0.0.0.0" --port 42014