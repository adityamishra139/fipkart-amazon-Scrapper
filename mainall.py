import requests
from bs4 import BeautifulSoup
import datetime
import gspread
import sys
from google.oauth2.service_account import Credentials
import time
sys.stdout.reconfigure(encoding='utf-8')

# Google Sheets API setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'credentials.json'  # Update this path

credentials = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(credentials)

# Your spreadsheet ID and the sheet names
SPREADSHEET_ID = '1SjEqepPqygtUDzojAA23AYA93AtS_RcCPojnDTT3piA'  # Update this ID
SHEET1_NAME = 'Sheet1'  # Update this name if 


SHEET2_NAME = 'Sheet2'  # Update this name if necessary

# Function to get the HTML content of the page with retries
def get_page_content(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT; Windows NT 6.2; en-US) WindowsPowerShell/4.0",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",  # Do Not Track Request Header
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.content.decode('utf-8', errors='replace')
        except requests.exceptions.HTTPError as e:
            if attempt < 2:
                print(f"Attempt {attempt+1} failed: {e}. Retrying...")
            else:
                print(f"Attempt {attempt+1} failed: {e}. No more retries.")
                raise

# Function to parse the HTML content and extract the price from Amazon
def parse_amazon_info(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    price_tag = soup.find('span', {'class': 'a-offscreen'})
    price = price_tag.get_text(strip=True) if price_tag else "Price not found"
    return price.replace('₹', '').strip()

# Function to parse the HTML content and extract the price from Flipkart
def parse_flipkart_info(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    price_tag = soup.find('div', {'class': 'Nx9bqj CxhGGd'})
    price = price_tag.get_text(strip=True) if price_tag else "Price not found"
    return price.replace('₹', '').strip()

#Function to parse the HTML content and extract the price from Blinkit
def parse_blinkit_info(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    # Use partial match to find the price container
    price_tag = soup.find('div', {'class': lambda x: x and 'ProductVariants__PriceContainer' in x})
    if price_tag:
        price_text = price_tag.get_text(strip=True)
        price = price_text.split()[0]  # Gets '₹1199' from the text
    else:
        price = "Price not found"
    return price.replace('₹', '').strip()

#Function to parse the HTML content and extract the price from Zepto
def parse_zepto_info(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    # Look for the price directly with its unique combination of classes
    price_tag = soup.find('span', {
        'class': lambda x: x and all(cls in x for cls in [
            'text-[32px]',
            'font-medium',
            'text-[#262A33]'
        ])
    })
    
    if price_tag:
        price = price_tag.get_text(strip=True)
    else:
        price = "Price not found"
    
    return price.replace('₹', '').strip()


def parse_kreo_tech_info(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    price_tag = soup.find('span', {'class': 'price-item price-item--sale price-item--last'})
    price = price_tag.get_text(strip=True) if price_tag else "Price not found"
    return price.replace('₹', '').strip()

# Main function to update Google Sheets
def update_google_sheet():
    try:
        sheet1 = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET1_NAME)
        sheet2 = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET2_NAME)

        products_data = sheet2.get_all_values()
        total_products = len(products_data) - 1

        current_date = datetime.datetime.now().strftime("%d/%m/%y")

        for i in range(1, len(products_data)):
            try:
                print(f"\nProcessing product {i} of {total_products}")
                product = products_data[i][0]
                amazon_url = products_data[i][1]
                flipkart_url = products_data[i][2]
                kreo_tech_url = products_data[i][3]
                zepto_url = products_data[i][4]
                blinkit_url = products_data[i][5]

                print(f"Processing product: {product}")

                # Get Amazon price
                amazon_price = "-"
                if amazon_url:
                    content = get_page_content(amazon_url)
                    if content:
                        amazon_price = parse_amazon_info(content)
                        print(f"Amazon price fetched: {amazon_price}")

                # Get Flipkart price
                flipkart_price = "-"
                if flipkart_url:
                    content = get_page_content(flipkart_url)
                    if content:
                        flipkart_price = parse_flipkart_info(content)
                        print(f"Flipkart price fetched: {flipkart_price}")

                # Get Kreo Tech price
                kreo_tech_price = "-"
                if kreo_tech_url:
                    kreo_tech_price = parse_kreo_tech_info(kreo_tech_url)
                    print(f"Kreo Tech price fetched: {kreo_tech_price}")

                # Get Zepto price
                zepto_price = "-"
                if zepto_url:
                    content = get_page_content(zepto_url)
                    if content:
                        zepto_price = parse_zepto_info(content)
                        print(f"Zepto price fetched: {zepto_price}")

                # Get Blinkit price
                blinkit_price = "-"
                if blinkit_url:
                    content = get_page_content(blinkit_url)
                    if content:
                        blinkit_price = parse_blinkit_info(content)
                        print(f"Blinkit price fetched: {blinkit_price}")

                # Create and append the new row
                new_row = [product, current_date, amazon_price, flipkart_price, 
                          kreo_tech_price, zepto_price, blinkit_price]
                
                try:
                    sheet1.append_row(new_row)
                    print(f"Successfully updated sheet for product: {product}")
                except Exception as e:
                    print(f"Error updating sheet for product {product}: {e}")
                    continue

            except Exception as e:
                print(f"Error processing product {product}: {e}")
                continue

    except Exception as e:
        print(f"Fatal error in update_google_sheet: {e}")
        raise

if __name__ == "__main__":
    update_google_sheet()
