"""Sanity check for the Colab runtime:  uv run colab run examples/gpu_check.py"""

import time

import torch

print("torch", torch.__version__, "| CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    props = torch.cuda.get_device_properties(0)
    print(f"GPU: {props.name}, {props.total_memory / 1e9:.1f} GB")
    a = torch.randn(8192, 8192, device="cuda", dtype=torch.float16)
    torch.cuda.synchronize()
    start = time.perf_counter()
    for _ in range(10):
        a @ a
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - start
    print(f"fp16 matmul: {10 * 2 * 8192**3 / elapsed / 1e12:.1f} TFLOPS")
