import subprocess
import os
import sys

# Configuration
HERMES_BIN = "/home/cxiong/.hermes/hermes-agent/venv/bin/hermes"
PROFILE = "jarvis"
MODEL = "/vllm_models/gemma-4-31B-it-FP8"
PROVIDER = "gpu_2"
ENV_VARS = os.environ.copy()
ENV_VARS["HERMES_HOME"] = "/home/cxiong/.hermes"

def launch():
    print(f"Launching Jarvis Strategist on profile {PROFILE}...")
    
    # We use 'gateway run' but we ensure it is wrapped in a way 
    # that the process is managed and the environment is locked.
    cmd = [
        HERMES_BIN, 
        "gateway", 
        "run", 
        "--profile", PROFILE,
        "-m", MODEL,
        "--provider", PROVIDER
    ]
    
    try:
        # We use Popen to keep it running in the background
        process = subprocess.Popen(
            cmd, 
            env=ENV_VARS, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        print(f"Jarvis Brain started with PID: {process.pid}")
        return process
    except Exception as e:
        print(f"Failed to launch Jarvis: {e}")
        sys.exit(1)

if __name__ == "__main__":
    launch()
