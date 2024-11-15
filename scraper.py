import requests
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime
import re
from typing import List, Dict
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_database():
    conn = sqlite3.connect('price_tracker.db')
    c = conn.cursor()
    
    # Create products table
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            url TEXT UNIQUE,
            name TEXT
        )
    ''')
    
    # Create price_history table
    c.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY,
            product_id INTEGER,
            shop_name TEXT,
            price REAL,
            amount TEXT,
            price_per_gram REAL,
            expiration TEXT,
            shops_valid TEXT,
            additional_note TEXT,
            fetch_timestamp DATETIME,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    
    conn.commit()
    return conn

def parse_amount(amount_str: str) -> float:
    """Extract numeric value from amount string (e.g., '100 g' -> 100.0)"""
    match = re.search(r'(\d+(?:\.\d+)?)', amount_str)
    if match:
        return float(match.group(1))
    return 0.0

def parse_price(price_str: str) -> float:
    """Convert price string to float (e.g., '29,90 Kč' -> 29.90)"""
    price_str = price_str.replace(',', '.').replace('Kč', '').strip()
    try:
        return float(price_str)
    except ValueError:
        return 0.0

def scrape_product(url: str) -> Dict:
    """Scrape single product page"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Get product name
    product_name = soup.find('h1').get_text(strip=True) if soup.find('h1') else "Unknown Product"
    
    container = soup.find('table', class_='wide discounts_table')
    if not container:
        return {"name": product_name, "discounts": []}
    
    discounts = []
    rows = container.find_all('tr', class_='discount_row')
    
    for row in rows:
        shop_name_elem = row.find('span', class_='discounts_shop_name')
        shop_name = shop_name_elem.find('span').get_text(strip=True) if shop_name_elem else "N/A"
        
        price_elem = row.find('strong', class_='discount_price_value')
        price = price_elem.get_text(strip=True) if price_elem else "N/A"
        
        amount_elem = row.find('div', class_='discount_amount')
        amount = amount_elem.get_text(strip=True).replace('/', '').strip() if amount_elem else "N/A"
        
        # Calculate price per gram
        price_value = parse_price(price)
        amount_value = parse_amount(amount)
        price_per_gram = price_value / amount_value if amount_value > 0 else 0
        
        validity_elem = row.find('td', class_='discounts_validity')
        validity_span = validity_elem.find('span') if validity_elem else None
        expiration = validity_span.get_text(strip=True) if validity_span else "N/A"
        
        markets_elem = row.find('div', class_='discounts_markets')
        markets_link = markets_elem.find('a') if markets_elem else None
        shops_valid = markets_link.get_text(strip=True) if markets_link else "N/A"
        
        note_elem = row.find('div', class_='discount_note')
        note = note_elem.get_text(strip=True) if note_elem else ""
        
        discounts.append({
            "shop_name": shop_name,
            "price": price,
            "amount": amount,
            "price_per_gram": price_per_gram,
            "expiration": expiration,
            "shops_valid": shops_valid,
            "additional_note": note
        })
    
    return {"name": product_name, "discounts": discounts}

def save_to_database(conn, url: str, product_data: Dict):
    """Save scraped data to database"""
    c = conn.cursor()
    
    # Insert or update product
    c.execute('''
        INSERT OR IGNORE INTO products (url, name)
        VALUES (?, ?)
    ''', (url, product_data['name']))
    
    c.execute('SELECT id FROM products WHERE url = ?', (url,))
    product_id = c.fetchone()[0]
    
    # Insert price history
    timestamp = datetime.now().isoformat()
    for discount in product_data['discounts']:
        c.execute('''
            INSERT INTO price_history 
            (product_id, shop_name, price, amount, price_per_gram, expiration, 
             shops_valid, additional_note, fetch_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            product_id,
            discount['shop_name'],
            parse_price(discount['price']),
            discount['amount'],
            discount['price_per_gram'],
            discount['expiration'],
            discount['shops_valid'],
            discount['additional_note'],
            timestamp
        ))
    
    conn.commit()

def scrape_all_products():
    """Function to scrape all products - this is what app.py expects"""
    logger.info("Starting to scrape all products...")
    urls = [
        'https://www.kupi.cz/sleva/tunak-v-oleji-rio-mare',
        'https://www.kupi.cz/sleva/cokolada-studentska-pecet-orion',
        'https://www.kupi.cz/sleva/zlate-polomacene-opavia',
        'https://www.kupi.cz/sleva/cokopiskoty-figaro'
    ]
    
    conn = setup_database()
    
    for url in urls:
        try:
            logger.info(f"Scraping {url}...")
            product_data = scrape_product(url)
            save_to_database(conn, url, product_data)
            logger.info(f"Successfully processed: {product_data['name']}")
        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}")
    
    conn.close()
    logger.info("Scraping completed!")

if __name__ == '__main__':
    scrape_all_products()