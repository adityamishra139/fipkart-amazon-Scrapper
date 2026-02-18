import requests
from bs4 import BeautifulSoup
import datetime
import gspread
import sys
from google.oauth2.service_account import Credentials
sys.stdout.reconfigure(encoding='utf-8')

# Google Sheets API setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'credentials.json'  # Update this path

credentials = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(credentials)

SPREADSHEET_ID = '1wJCRmIApGpgDQv_P0QbRasFowPYjuiLjAaCA1NLMGJs'  # Update this ID
SHEET1_NAME = 'Sheet1'  # Update this name if necessary
SHEET2_NAME = 'Sheet2' 


def get_page_content(url):
    print('Fetching Data...', url)
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
    
    # Extract the price
    price_tag = soup.find('a', {'class': 'a-offscreen'})
    price = price_tag.get_text(strip=True) if price_tag else "Price not found"

    # Try different methods to extract the seller information
    soldby_tag = soup.find('a', {'id': 'sellerProfileTriggerId'})
    
    if not soldby_tag:
        # Try to search for any relevant "Sold by" text in other parts of the HTML
        soldby_section = soup.find('div', {'class': 'tabular-buybox-text'})
        if soldby_section:
            soldby_tag = soldby_section.find('a')  # Look for any <a> tag within the section
    
    # Extract seller info or default to not found
    soldby = soldby_tag.get_text(strip=True) if soldby_tag else "Seller not found"
    
    return price.replace('₹', '').strip(), soldby.strip()

# Function to parse the HTML content and extract the price from Flipkart
def parse_flipkart_info(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    price_tag = soup.find('div', {'class': 'Nx9bqj CxhGGd'})
    price = price_tag.get_text(strip=True) if price_tag else "Price not found"
    return price.replace('₹', '').strip()

# Function to parse the HTML content and extract the price from Kreo Tech
def parse_kreo_tech_info(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    price_tag = soup.find('span', {'class': 'price-item price-item--sale price-item--last'})
    price = price_tag.get_text(strip=True) if price_tag else "Price not found"
    return price.replace('₹', '').strip()

# Main function to update Google Sheets
def update_google_sheet():
    # Open the Google Sheets
    sheet1 = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET1_NAME)
    sheet2 = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET2_NAME)

    # Read all product data from Sheet2
    products_data = sheet2.get_all_values()

    # Get the current date
    current_date = datetime.datetime.now().strftime("%d/%m/%y")

    # Prepare the new rows to be appended
    new_rows = []

    # Loop through each row in the products data (skip the header row)
    for i in range(1, len(products_data)):
        product = products_data[i][0]
        amazon_url = products_data[i][1]
        flipkart_url = products_data[i][2]
        kreo_tech_url = products_data[i][3]

        try:
            # Fetch the prices
            amazon_price, amazon_soldby = parse_amazon_info(get_page_content(amazon_url))
        except requests.exceptions.RequestException as e:
            amazon_price = f"Error: {e}"

        try:
            flipkart_price = parse_flipkart_info(get_page_content(flipkart_url))
        except requests.exceptions.RequestException as e:
            flipkart_price = f"Error: {e}"

        try:
            kreo_tech_price = parse_kreo_tech_info(kreo_tech_url)
        except requests.exceptions.RequestException as e:
            kreo_tech_price = f"Error: {e}"

        # Create a new row with the fetched prices
        new_row = [product, current_date, amazon_price, flipkart_price, kreo_tech_price,amazon_soldby]
        new_rows.append(new_row)

    # Append the new rows to Sheet1
    sheet1.append_rows(new_rows)

if __name__ == "__main__":
    print('start')
    update_google_sheet()
