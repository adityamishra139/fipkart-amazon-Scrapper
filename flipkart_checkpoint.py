import requests
from bs4 import BeautifulSoup
import gspread
import sys
from google.oauth2.service_account import Credentials
import time
import random

sys.stdout.reconfigure(encoding='utf-8')

# OAuth setup
try:
    client = gspread.oauth(
        credentials_filename='credentials.json',
        authorized_user_filename='token.json'
    )
except Exception as e:
    print("Error during OAuth login. Make sure you have the 'OAuth Client ID' json saved as 'credentials.json'")
    print(f"Details: {e}")
    sys.exit(1)

# Your spreadsheet ID and specific Worksheet GID
SPREADSHEET_ID = '1ecfNJT5t4YkT0RTuZ8-O2s0PXQVsl4z6UWB9R4l_UVs'
WORKSHEET_GID = 733063400

# Function to get the HTML content of the page with retries
def get_page_content(url):
    import random
    import time
    
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
    
    time.sleep(random.uniform(4, 8))

    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.content.decode('utf-8', errors='replace')
        except requests.exceptions.HTTPError as e:
            if attempt < 2:
                print(f"Attempt {attempt+1} failed: {e}. Retrying...")
                time.sleep(random.uniform(5, 10))
            else:
                print(f"Attempt {attempt+1} failed: {e}. No more retries.")
                raise

# Function to parse the HTML content and extract the price from Flipkart
def parse_flipkart_info(html_content, row_id=None):
    from lxml import html
    
    try:
        tree = html.fromstring(html_content)
        
        # Strategy 1: User's Specific XPath 1
        xpath_1 = '/html/body/div[1]/div/div[1]/div/div/div/div/div/div/div/div/div/div/div[2]/div/div[2]/div/div/div/div[1]/div/div[2]/div/div[6]/div/div/div/div/div/div/div/div/div/div/div/a[1]/div/div[3]/div'
        res1 = tree.xpath(xpath_1)
        if res1:
            return res1[0].text_content().replace('₹', '').replace(',', '').strip()

        # Strategy 2: User's Specific XPath 2
        xpath_2 = '/html/body/div[1]/div/div[1]/div/div/div/div/div/div/div/div/div/div/div[2]/div/div[2]/div/div/div/div[1]/div/div[2]/div/div[5]/div/div/div/div/div/div/div/div/div/div/div/a/div/div[3]/div'
        res2 = tree.xpath(xpath_2)
        if res2:
            return res2[0].text_content().replace('₹', '').replace(',', '').strip()

        # Strategy 3: User's Specific XPath 3 (New pattern with div[4])
        xpath_3 = '/html/body/div[1]/div/div[1]/div/div/div/div/div/div/div/div/div/div/div[2]/div/div[2]/div/div/div/div[1]/div/div[2]/div/div[4]/div/div/div/div/div/div/div/div/div/div/div/a/div/div[3]/div'
        res3 = tree.xpath(xpath_3)
        if res3:
            return res3[0].text_content().replace('₹', '').replace(',', '').strip()

        # Strategy 4: Common class "Nx9bqj CxhGGd" (Fallback)
        price_tags = tree.xpath('//div[contains(@class, "Nx9bqj") and contains(@class, "CxhGGd")]')
        if price_tags:
            return price_tags[0].text_content().replace('₹', '').replace(',', '').strip()

        # Strategy 4: Older common class "_30jeq3 _1_WHN1" (Fallback)
        price_tags = tree.xpath('//div[contains(@class, "_30jeq3") and contains(@class, "_1_WHN1")]')
        if price_tags:
            return price_tags[0].text_content().replace('₹', '').replace(',', '').strip()
            
        # Strategy 5: Just "Nx9bqj"
        price_tags = tree.xpath('//div[contains(@class, "Nx9bqj")]')
        if price_tags:
            return price_tags[0].text_content().replace('₹', '').replace(',', '').strip()

    except Exception as e:
        print(f"Error parsing Flipkart with lxml: {e}")
        pass

    # Fallback to BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    classes_to_try = ['Nx9bqj CxhGGd', '_30jeq3 _1_WHN1', 'Nx9bqj', '_30jeq3']
    for cls in classes_to_try:
        price_tag = soup.find('div', {'class': cls})
        if price_tag:
            return price_tag.get_text(strip=True).replace('₹', '').strip()

    # Strategy 6: JSON-LD (Script tag)
    try:
        import json
        json_ld_scripts = soup.find_all('script', {'type': 'application/ld+json'})
        for script in json_ld_scripts:
            if script.string:
                try:
                    data = json.loads(script.string)
                    # Data can be a list or a dict
                    if isinstance(data, list):
                        data = data[0]
                    
                    if isinstance(data, dict):
                        # Check for "offers" -> "price"
                        if "offers" in data and "price" in data["offers"]:
                            return str(data["offers"]["price"])
                        # Sometimes it's directly in the object if schema is just Product
                        if "price" in data:
                            return str(data["price"])
                except Exception as inner_e:
                    continue
    except Exception as e:
        print(f"Error parsing JSON-LD: {e}")
        pass
            
    # Debug: Save HTML for analysis if not found
    if row_id:
        filename = f"debug_failed_row_{row_id}_flipkart.html"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"Row {row_id}: Flipkart Price not found. Saved debug html to {filename}")
        except Exception as e:
            print(f"Error saving debug file: {e}")
            
    return "Price not found"

def update_google_sheet():
    try:
        sh = client.open_by_key(SPREADSHEET_ID)
        worksheet = sh.get_worksheet_by_id(WORKSHEET_GID)
        
        print(f"Opened worksheet: {worksheet.title}")

        all_values = worksheet.get_all_values()
        
        # Start from row 2
        for i, row in enumerate(all_values[1:], start=2):
            any_updated = False
            
            # --- Flipkart Processing (Column F -> Column G) ---
            # Column F is index 5
            flipkart_url = ""
            if len(row) > 5:
                flipkart_url = row[5].strip()
            
            if flipkart_url and "flipkart" in flipkart_url:
                try:
                    print(f"Row {i}: Fetching Flipkart price for {flipkart_url}")
                    content = get_page_content(flipkart_url)
                    if content:
                        price = parse_flipkart_info(content, row_id=i)
                        try:
                            # Update Column G (index 7 in 1-based API)
                            worksheet.update_cell(i, 7, price)
                            print(f"Row {i}: Updated Flipkart Price (Col G): {price}")
                            any_updated = True
                        except Exception as e:
                            print(f"Row {i}: Error updating Flipkart cell: {e}")
                except Exception as e:
                    print(f"Row {i}: Error processing Flipkart URL: {e}")
                    try:
                        worksheet.update_cell(i, 7, "Error")
                    except: pass
            
            # Rate limiting
            if any_updated:
                time.sleep(1)

    except Exception as e:
        print(f"Fatal error in update_google_sheet: {e}")
        raise

if __name__ == "__main__":
    update_google_sheet()
