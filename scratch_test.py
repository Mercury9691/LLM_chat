import json
import requests
import sys

def test_qwen():
    url = "http://10.10.11.21:8080/v1/chat/completions"
    payload = {
        "model": "Qwen3.5-122B-A10B-FP8",
        "messages": [{"role": "user", "content": "15 * 18 = ? Please think step by step."}],
        "stream": True,
        "temperature": 0.7,
        "top_p": 0.9,
    }
    
    try:
        r = requests.post(url, json=payload, stream=True)
        print(f"Status Code: {r.status_code}")
        for line in r.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                print(decoded_line)
                if len(decoded_line) > 500:
                    break
    except Exception as e:
        print(e)

if __name__ == "__main__":
    test_qwen()
