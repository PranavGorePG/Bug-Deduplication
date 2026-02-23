import requests
import json
import sys

# Define the endpoint URL
url = "http://127.0.0.1:8001/process-json"

# Define sample bug reports
bug_reports = [
    {
        "id": 1001,
        "title": "Application crashes on startup",
        "repro_steps": "1. Launch app\n2. Wait for loading screen\n3. Observe crash",
        "module": "Core"
    },
    {
        "id": 1002,
        "title": "Login button not working",
        "repro_steps": "1. Go to login screen\n2. Enter credentials\n3. Click Login button\n4. Nothing happens",
        "module": "Auth"
    }
]

def verify_json_endpoint():
    print(f"Sending request to {url}...")
    try:
        response = requests.post(url, json=bug_reports)
        
        if response.status_code == 200:
            print("Request successful!")
            results = response.json()
            print(f"Received {len(results)} results.")
            
            # Save to file for inspection
            with open("verification_result.json", "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            print("Saved results to verification_result.json")
            
            for i, result in enumerate(results):
                print(f"\nResult {i+1}:")
                # print(json.dumps(result, indent=2))
                print(f"Result: {result.get('result')}")
                # check matches
                matches = result.get('matches', [])
                print(f"Matches count: {len(matches)}")
                for m in matches:
                     print(f"  Match ID: {m.get('id')}")
                     print(f"  Repro: '{m.get('repro_steps', 'MISSING')}'")
                
                # Basic validation of the response structure
                if "result" not in result:
                    print(f"Error: Result {i+1} missing 'result' field")
                    sys.exit(1)
            
            print("\nVerification Passed!")
        else:
            print(f"Request failed with status code: {response.status_code}")
            print(response.text)
            sys.exit(1)
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server. Make sure it's running.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_json_endpoint()
