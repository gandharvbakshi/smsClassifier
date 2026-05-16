import requests
import json
import time
import subprocess
import sys

def check_gpu_usage():
    """Check GPU usage using nvidia-smi"""
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total', '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            gpu_info = result.stdout.strip().split(', ')
            return {
                'gpu_util': f"{gpu_info[0]}%",
                'memory_used': f"{gpu_info[1]}MB",
                'memory_total': f"{gpu_info[2]}MB"
            }
    except Exception as e:
        return None
    return None

def test_gpu_usage():
    """Test if GPU is being used during inference"""
    print("="*80)
    print("TESTING GPU USAGE WITH DEEPSEEK-R1:8B")
    print("="*80)
    
    # Check GPU before
    print("\nGPU Status BEFORE inference:")
    gpu_before = check_gpu_usage()
    if gpu_before:
        print(f"  GPU Utilization: {gpu_before['gpu_util']}")
        print(f"  GPU Memory: {gpu_before['memory_used']} / {gpu_before['memory_total']}")
    else:
        print("  Could not get GPU info")
    
    # Make an API call
    print("\nMaking API call to deepseek-r1:8b...")
    prompt = "Classify this SMS: '765512 is OTP for txn of INR 239.89 at AMAZON on ICICI Bank Credit Card XX7350. OTPs are SECRET. DO NOT disclose it to anyone. Bank NEVER asks for OTP.' Respond ONLY with JSON: {\"is_otp\": true, \"otp_intent\": \"BANK_OR_CARD_TXN_OTP\"}"
    
    start_time = time.time()
    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'deepseek-r1:8b',
                'prompt': prompt,
                'stream': False
            },
            timeout=60
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"  Response received in {elapsed:.2f} seconds")
            print(f"  Response length: {len(result.get('response', ''))} chars")
        else:
            print(f"  Error: HTTP {response.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Check GPU during/after
    time.sleep(1)  # Wait a moment
    print("\nGPU Status AFTER inference:")
    gpu_after = check_gpu_usage()
    if gpu_after:
        print(f"  GPU Utilization: {gpu_after['gpu_util']}")
        print(f"  GPU Memory: {gpu_after['memory_used']} / {gpu_after['memory_total']}")
    
    print("\n" + "="*80)
    print("RECOMMENDATIONS:")
    print("="*80)
    print("""
1. Ollama should automatically use NVIDIA GPU if:
   - NVIDIA drivers are installed (✓ You have 581.80)
   - CUDA is available (✓ You have CUDA 13.0)
   - Model fits in GPU memory (✓ 8GB GPU should handle 8B model)

2. If you want to FORCE NVIDIA GPU usage:
   - Set environment variable: set CUDA_VISIBLE_DEVICES=0
   - Restart Ollama service
   - Check Ollama logs for GPU detection

3. Performance should be MUCH faster on GPU:
   - CPU: ~2-5 tokens/second
   - NVIDIA GPU: ~15-30 tokens/second (3-10x faster!)
   - Your RTX 4060 should handle the 8B model well

4. To verify GPU is being used:
   - Run 'nvidia-smi' in another terminal while processing
   - Watch GPU utilization spike during inference
   - Check GPU memory usage stays high (model loaded)
""")

if __name__ == "__main__":
    # Set UTF-8 encoding for stdout
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    test_gpu_usage()

