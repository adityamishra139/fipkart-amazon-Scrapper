import requests
from lxml import html

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
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}

try:
    response = requests.get(url, headers=headers, allow_redirects=True)
    print(f"Final URL: {response.url}")
    print(f"Status Code: {response.status_code}")
    
    content = response.content.decode('utf-8')
    tree = html.fromstring(content)
    
    # 1. Check User's XPath
    xpath_1 = '/html/body/div[1]/div[1]/div[2]/div[5]/div[4]/div[16]/div/div/div[4]/div[1]/span[1]'
    res1 = tree.xpath(xpath_1)
    print(f"Strategy 1 (Absolute XPath): {res1}")
    if res1:
        print(f"  Content: {res1[0].text_content()}")

    # 2. Check Relative XPath
    xpath_2 = '//div[@id="corePriceDisplay_desktop_feature_div"]//span[contains(@class, "offscreen")]'
    res2 = tree.xpath(xpath_2)
    print(f"Strategy 2 (Relative XPath): {res2}")
    if res2:
        for r in res2:
            print(f"  Content: {r.text_content()}")
            
    # 3. Check for specific ID existence
    centerCol = tree.xpath('//*[@id="centerCol"]')
    print(f"Has centerCol: {len(centerCol) > 0}")
    
    apex = tree.xpath('//*[@id="apex_desktop"]')
    print(f"Has apex_desktop: {len(apex) > 0}")

    corePrice = tree.xpath('//*[@id="corePriceDisplay_desktop_feature_div"]')
    print(f"Has corePriceDisplay: {len(corePrice) > 0}")
    
    # 4. Check for 'aok-offscreen' (User mentioned this class)
    aok_offscreen = tree.xpath('//span[contains(@class, "aok-offscreen")]')
    print(f"Strategy 4 (aok-offscreen): {len(aok_offscreen)} found")
    for node in aok_offscreen:
        print(f"  aok-offscreen content: {node.text_content().strip()}")

    # 5. Check for 'a-price-whole'
    price_whole = tree.xpath('//span[contains(@class, "a-price-whole")]')
    print(f"Strategy 5 (a-price-whole): {len(price_whole)} found")
    for node in price_whole:
        print(f"  a-price-whole content: {node.text_content().strip()}")

    # 6. Check for 'a-offscreen' generally
    a_offscreen = tree.xpath('//span[contains(@class, "a-offscreen")]')
    print(f"Strategy 6 (a-offscreen): {len(a_offscreen)} found")
    for node in a_offscreen:
        print(f"  a-offscreen content: {node.text_content().strip()}")

    # 7. Check hidden inputs
    hidden_input = tree.xpath('//input[@id="items[0.base][customerVisiblePrice][amount]"]/@value')
    print(f"Strategy 7 (hidden input): {hidden_input}")

    # Check if we are blocked
    if "api-services-support@amazon.com" in content:
        print("BLOCKED: Captcha detected.")
        
except Exception as e:
    print(f"Error: {e}")
