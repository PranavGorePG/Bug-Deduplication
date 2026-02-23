import requests

url = "http://127.0.0.1:8000/api/external-bugs"

try:
    print(f"Fetching from {url}...")
    response = requests.get(url)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Success! Received {len(data)} items.")
        print("First item sample:", data[0])
    else:
        print("Failed request.")
        print(response.text)
except Exception as e:
    print(f"Error: {e}")
