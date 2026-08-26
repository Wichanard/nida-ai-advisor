import requests

try:
    response = requests.post("http://127.0.0.1:8000/api/chat", json={"session_id":"test", "message":"hello"}, stream=True)
    for chunk in response.iter_content(chunk_size=1024):
        if chunk:
            print(chunk.decode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
