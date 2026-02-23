import requests

url = "https://untillable-tyra-monarchically.ngrok-free.dev/api/bugs/bugs-res-ai/e915b62d-b6b1-4780-b0e7-8320278991f2"

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
