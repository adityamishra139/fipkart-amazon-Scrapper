from bs4 import BeautifulSoup
import gspread
import sys
import time
import random
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

sys.stdout.reconfigure(encoding='utf-8')

# OAuth setup (runs as YOU, bypassing sharing restrictions)
# This will open a browser window the first time to log in.
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

# Function to get the HTML content of a page using Playwright (bypasses anti-bot)
def get_page_content(page, url):
    """Fetch page content using an existing Playwright page with stealth."""
    # Human-like delay between requests
    time.sleep(random.uniform(8, 15))
    
    for attempt in range(3):
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            # Wait a bit for dynamic content to load
            time.sleep(random.uniform(2, 4))
            content = page.content()
            return content
        except Exception as e:
            if attempt < 2:
                print(f"Attempt {attempt+1} failed: {e}. Retrying...")
                time.sleep(random.uniform(5, 10))
            else:
                print(f"Attempt {attempt+1} failed: {e}. No more retries.")
                raise

# Function to parse the HTML content and extract the price from Amazon
def parse_amazon_info(html_content, row_id=None):
    from lxml import html
    
    try:
        tree = html.fromstring(html_content)
        
        # Check for CAPTCHA/Block
        if "api-services-support@amazon.com" in html_content or "Enter the characters you see below" in html_content:
            print(f"Row {row_id}: BLOCKED by Amazon Captcha.")
            # Save it anyway to confirm
            if row_id:
                with open(f"debug_blocked_row_{row_id}_amazon.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
            return "Blocked"

        # Check for "Currently unavailable"
        if "Currently unavailable" in html_content:
            # check if it really is unavailable (sometimes text exists in other places)
            availability = tree.xpath('//div[@id="availability"]/span')
            if availability and "Currently unavailable" in availability[0].text_content():
                return "Out of Stock"
        
        # Strategy 1: User's Specific Absolute XPath
        # /html/body/div[1]/div[1]/div[2]/div[5]/div[4]/div[16]/div/div/div[4]/div[1]/span[1]
        xpath_result = tree.xpath('/html/body/div[1]/div[1]/div[2]/div[5]/div[4]/div[16]/div/div/div[4]/div[1]/span[1]')
        if xpath_result:
            return xpath_result[0].text_content().strip().replace('₹', '').replace(',', '')
        
        # Strategy 2: Relative XPath - Apex Desktop Container
        apex_xpath = tree.xpath('//div[@id="apex_desktop"]//span[contains(@class, "a-offscreen")]')
        if apex_xpath:
            for node in apex_xpath:
                text = node.text_content().strip().replace('₹', '').replace(',', '')
                if text and any(c.isdigit() for c in text):
                    return text

        # Strategy 3: Relative XPath - CorePriceDisplay
        relative_xpath = tree.xpath('//div[@id="corePriceDisplay_desktop_feature_div"]//span[contains(@class, "offscreen")]')
        if relative_xpath:
            for node in relative_xpath:
                text = node.text_content().strip().replace('₹', '').replace(',', '')
                if text and any(c.isdigit() for c in text):
                    return text

        # Strategy 4: Hidden input "items[0.base][customerVisiblePrice][amount]"
        hidden_input = tree.xpath('//input[@id="items[0.base][customerVisiblePrice][amount]"]/@value')
        if hidden_input:
            return hidden_input[0].strip()

        # Strategy 5: Fallback to searching all a-offscreen classes generally
        general_offscreen = tree.xpath('//span[contains(@class, "a-offscreen")]')
        for node in general_offscreen:
            text = node.text_content().strip().replace('₹', '').replace(',', '')
            if text and any(c.isdigit() for c in text) and len([c for c in text if c.isalpha()]) < 3:
                return text

        # Strategy 6: Other hidden inputs
        attach_price = tree.xpath('//input[@id="attach-base-product-price"]/@value')
        if attach_price: return attach_price[0].strip()
        
        twister_price = tree.xpath('//input[@id="twister-plus-price-data-price"]/@value')
        if twister_price: return twister_price[0].strip()
        
        # Strategy 7: a-price-whole
        price_whole = tree.xpath('//span[contains(@class, "a-price-whole")]')
        if price_whole:
            return price_whole[0].text_content().strip().replace('.', '').replace(',', '')

    except Exception as e:
        print(f"Error parsing with lxml: {e}")
        pass
    
    # Fallback to BeautifulSoup logic
    soup = BeautifulSoup(html_content, 'html.parser')
    
    price_input = soup.find('input', {'id': 'items[0.base][customerVisiblePrice][amount]'})
    if price_input and price_input.get('value'):
        return price_input['value'].strip()
        
    # Debug: Save HTML for analysis if not found
    if row_id:
        filename = f"debug_failed_row_{row_id}.html"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"Row {row_id}: Price not found. Saved debug html to {filename}")
        except Exception as e:
            print(f"Error saving debug file: {e}")
        
    return "Price not found"

# Function to parse the HTML content and extract the price from Flipkart
def parse_flipkart_info(html_content, row_id=None):
    from lxml import html
    
    try:
        tree = html.fromstring(html_content)
        
        # Strategy 1: Current common class "Nx9bqj CxhGGd"
        price_tags = tree.xpath('//div[contains(@class, "Nx9bqj") and contains(@class, "CxhGGd")]')
        if price_tags:
            return price_tags[0].text_content().replace('₹', '').replace(',', '').strip()

        # Strategy 2: Older common class "_30jeq3 _1_WHN1"
        price_tags = tree.xpath('//div[contains(@class, "_30jeq3") and contains(@class, "_1_WHN1")]')
        if price_tags:
            return price_tags[0].text_content().replace('₹', '').replace(',', '').strip()
            
        # Strategy 3: Just "_30jeq3" or "Nx9bqj"
        price_tags = tree.xpath('//div[contains(@class, "Nx9bqj")]')
        if price_tags:
            return price_tags[0].text_content().replace('₹', '').replace(',', '').strip()
            
        price_tags = tree.xpath('//div[contains(@class, "_30jeq3")]')
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

# Function to parse the HTML content and extract the price from Amazon
def parse_amazon_info(html_content, row_id=None):
    from lxml import html
    
    try:
        tree = html.fromstring(html_content)
        
        # Check for "Currently unavailable"
        if "Currently unavailable" in html_content:
            # check if it really is unavailable (sometimes text exists in other places)
            availability = tree.xpath('//div[@id="availability"]/span')
            if availability and "Currently unavailable" in availability[0].text_content():
                return "Out of Stock"
        
        # Strategy 0 (NEW): User's "aok-offscreen" (Explicitly requested for discounted price)
        aok_offscreen = tree.xpath('//span[contains(@class, "aok-offscreen")]')
        if aok_offscreen:
            import re
            text = aok_offscreen[0].text_content().strip()
            # Extract basic price pattern: digits, commas, maybe dot
            match = re.search(r'[0-9,.]+', text)
            if match:
                price_str = match.group(0).replace(',', '')
                try:
                    # distinct handling for float to int conversion to avoid 7290.00 issues
                    return str(int(float(price_str)))
                except:
                    return price_str

        # Strategy 0.5 (NEW): "a-price-whole" (Standard Amazon price element)
        price_whole = tree.xpath('//span[contains(@class, "a-price-whole")]')
        if price_whole:
            return price_whole[0].text_content().strip().replace('.', '').replace(',', '')

        # Strategy 1: User's Specific Absolute XPath
        # /html/body/div[1]/div[1]/div[2]/div[5]/div[4]/div[16]/div/div/div[4]/div[1]/span[1]
        # Note: XPath indices are 1-based.
        # We need to handle cases where the user meant "rupee symbol is here, price is next to it"
        # The user said: "span HTML where : <span class="aok-offscreen"> contains the price"
        xpath_result = tree.xpath('/html/body/div[1]/div[1]/div[2]/div[5]/div[4]/div[16]/div/div/div[4]/div[1]/span[1]')
        if xpath_result:
            return xpath_result[0].text_content().strip().replace('₹', '').replace(',', '')

        # Strategy 2: Relative XPath - Apex Desktop Container (Found in debug to exist)
        # We search for a-offscreen INSIDE apex_desktop, as corePriceDisplay might be missing or named differently
        apex_xpath = tree.xpath('//div[@id="apex_desktop"]//span[contains(@class, "a-offscreen")]')
        if apex_xpath:
            for node in apex_xpath:
                text = node.text_content().strip().replace('₹', '').replace(',', '')
                if text and any(c.isdigit() for c in text):
                    return text

        # Strategy 3: Relative XPath - CorePriceDisplay (User's ID)
        # "corePriceDisplay_desktop_feature_div" -> "a-section..." -> "a-offscreen"
        # The user mentioned class "aok-offscreen" in their text, but "a-offscreen" in previous valid scraps. 
        # We'll check for both classes just in case.
        relative_xpath = tree.xpath('//div[@id="corePriceDisplay_desktop_feature_div"]//span[contains(@class, "offscreen")]')
        if relative_xpath:
            # Iterating to find the one with digits
            for node in relative_xpath:
                text = node.text_content().strip().replace('₹', '').replace(',', '')
                if text and any(c.isdigit() for c in text):
                    return text

        # Strategy 4: Hidden input "items[0.base][customerVisiblePrice][amount]"
        # XPath: //input[@id='items[0.base][customerVisiblePrice][amount]']/@value
        hidden_input = tree.xpath('//input[@id="items[0.base][customerVisiblePrice][amount]"]/@value')
        if hidden_input:
            return hidden_input[0].strip()

        # Strategy 5: Fallback to searching all a-offscreen classes generally
        general_offscreen = tree.xpath('//span[contains(@class, "a-offscreen")]')
        for node in general_offscreen:
            text = node.text_content().strip().replace('₹', '').replace(',', '')
            if text and any(c.isdigit() for c in text) and len([c for c in text if c.isalpha()]) < 3:
                return text

        # Strategy 6: Other hidden inputs
        attach_price = tree.xpath('//input[@id="attach-base-product-price"]/@value')
        if attach_price: return attach_price[0].strip()
        
        twister_price = tree.xpath('//input[@id="twister-plus-price-data-price"]/@value')
        if twister_price: return twister_price[0].strip()
        
        # Strategy 7: a-price-whole
        price_whole = tree.xpath('//span[contains(@class, "a-price-whole")]')
        if price_whole:
            return price_whole[0].text_content().strip().replace('.', '').replace(',', '')

    except Exception as e:
        print(f"Error parsing with lxml: {e}")
        # Fallback to BeautifulSoup if lxml fails for some reason
        pass
    
    # Fallback to BeautifulSoup logic if lxml completely fails
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Check hidden inputs again
    price_input = soup.find('input', {'id': 'items[0.base][customerVisiblePrice][amount]'})
    if price_input and price_input.get('value'):
        return price_input['value'].strip()
        
    # Debug: Save HTML for analysis if not found
    if row_id:
        filename = f"debug_failed_row_{row_id}.html"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"Row {row_id}: Price not found. Saved debug html to {filename}")
        except Exception as e:
            print(f"Error saving debug file: {e}")
        
    return "Price not found"

# Function to parse the HTML content and extract the price from Flipkart
def parse_flipkart_info(html_content):
    from lxml import html
    
    try:
        tree = html.fromstring(html_content)
        
        # Strategy 1: Current common class "Nx9bqj CxhGGd"
        # XPath: //div[@class="Nx9bqj CxhGGd"]
        price_tags = tree.xpath('//div[contains(@class, "Nx9bqj") and contains(@class, "CxhGGd")]')
        if price_tags:
            return price_tags[0].text_content().replace('₹', '').replace(',', '').strip()

        # Strategy 2: Older common class "_30jeq3 _1_WHN1"
        price_tags = tree.xpath('//div[contains(@class, "_30jeq3") and contains(@class, "_1_WHN1")]')
        if price_tags:
            return price_tags[0].text_content().replace('₹', '').replace(',', '').strip()
            
        # Strategy 3: Just "_30jeq3" or "Nx9bqj"
        price_tags = tree.xpath('//div[contains(@class, "Nx9bqj")]')
        if price_tags:
            return price_tags[0].text_content().replace('₹', '').replace(',', '').strip()
            
        price_tags = tree.xpath('//div[contains(@class, "_30jeq3")]')
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
            
    return "Price not found"

# NOTE: Other scrapers (Kreo, Zepto, Blinkit) are currently disabled.
# def parse_kreo_tech_info(url):
#     ...

# Main function to update Google Sheets
def update_google_sheet():
    # Launch Playwright browser once and reuse for all requests
    stealth = Stealth()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-IN',
        )
        stealth.apply_stealth_sync(context)
        page = context.new_page()
        
        print("Browser launched with stealth mode.")

        try:
            sh = client.open_by_key(SPREADSHEET_ID)
            worksheet = sh.get_worksheet_by_id(WORKSHEET_GID)
            
            print(f"Opened worksheet: {worksheet.title}")

            all_values = worksheet.get_all_values()
            
            for i, row in enumerate(all_values[1:], start=2):
                any_updated = False
                
                # --- Amazon Processing (Column B -> Column C) ---
                amazon_url = ""
                if len(row) > 1:
                    amazon_url = row[1].strip()
                
                if amazon_url and ("amazon" in amazon_url or "amzn" in amazon_url):
                    try:
                        print(f"Row {i}: Fetching Amazon price for {amazon_url}")
                        content = get_page_content(page, amazon_url)
                        if content:
                            price = parse_amazon_info(content, row_id=i)
                            try:
                                worksheet.update_cell(i, 3, price)
                                print(f"Row {i}: Updated Amazon Price (Col C): {price}")
                                any_updated = True
                            except Exception as e:
                                print(f"Row {i}: Error updating Amazon cell: {e}")
                    except Exception as e:
                        print(f"Row {i}: Error processing Amazon URL: {e}")
                        try:
                            worksheet.update_cell(i, 3, "Error")
                        except: pass

                # Rate limiting if we did any scraping
                if any_updated:
                    time.sleep(1)

        except Exception as e:
            print(f"Fatal error in update_google_sheet: {e}")
            raise
        finally:
            browser.close()
            print("Browser closed.")

if __name__ == "__main__":
    update_google_sheet()

