#!/bin/bash
# Fix for PyTorch CUDA library dependencies on this cluster
export LD_LIBRARY_PATH=/usr/local/cuda-12.9/targets/x86_64-linux/lib:$LD_LIBRARY_PATH
export CUDA_VISIBLE_DEVICES=""
python3 /home/cxiong/mnist_progression/mnist_app_v2.py
