import requests
from main import parse_amazon_info

url = "https://amzn.in/d/813fXi2"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

print(f"Fetching URL: {url}")
try:
    response = requests.get(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        price = parse_amazon_info(response.content.decode('utf-8'))
        print(f"Extracted Price: {price}")
        if price == "7290":
            print("SUCCESS: Correct discounted price fetched.")
        else:
            print(f"FAILURE: Expected 7290, got {price}")
    else:
        print("Failed to fetch page.")
except Exception as e:
    print(f"Error: {e}")
