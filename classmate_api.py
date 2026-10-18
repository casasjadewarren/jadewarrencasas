
import requests

url = "https://balcenajessicaann.onrender.com/profile"

try:
    response = requests.get(url, timeout=30)

    print("=" * 35)
    print("       CLASSMATE API CLIENT")
    print("=" * 35)
    print("Status Code:", response.status_code)

    if response.status_code == 200:
        try:
            data = response.json()

            print("\nAPI CONNECTION SUCCESSFUL!")
            print("-" * 35)

            if isinstance(data, dict):
                for key, value in data.items():
                    print(f"{key.replace('_', ' ').title()}: {value}")
            else:
                print(data)

            print("-" * 35)

        except ValueError:
            print("\nResponse is not JSON.")
            print("Response:", response.text)

    else:
        print("\nRequest failed.")
        print("Response:", response.text)

except requests.exceptions.RequestException as error:
    print("Connection error:", error)
