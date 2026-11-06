import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

username = os.getenv("NRE_USERNAME")
password = os.getenv("NRE_PASSWORD")
metrics_url = os.getenv("HSP_METRICS_URL")

if not username or not password or not metrics_url:
    print("Error: Missing environment variables in .env file.")
    exit(1)

headers = {"Content-Type": "application/json", "User-Agent": "TrackRecordApp/1.0"}

# Narrowed 2-day date window for a faster initial server response
payload = {
    "from_loc": "HML",
    "to_loc": "EUS",
    "from_time": "0700",
    "to_time": "0900",
    "from_date": "2026-10-12",
    "to_date": "2026-10-13",
    "days": "WEEKDAY",
}

print("Sending request to HSP API (timeout set to 30s)...")

try:
    response = requests.post(
        metrics_url.strip(),
        auth=(username, password),
        headers=headers,
        json=payload,
        timeout=30,  # Increased timeout to allow backend aggregation
    )

    print(f"HTTP Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print("Successfully retrieved data!")
        print("Response Keys:", list(data.keys()))

        os.makedirs("fixtures", exist_ok=True)
        fixture_path = os.path.join("fixtures", "hsp_sample.json")

        with open(fixture_path, "w") as f:
            json.dump(data, f, indent=2)

        print(f"Saved sample fixture to {fixture_path}")
    else:
        print(f"Request failed ({response.status_code}): {response.text[:200]}")

except requests.exceptions.Timeout:
    print("Error: The request timed out after 30 seconds.")
except requests.exceptions.RequestException as e:
    print(f"Network error occurred: {e}")
