import requests
from bs4 import BeautifulSoup
import json
from typing import Dict, List, Tuple

def scrape_website() -> Tuple[str, List[Dict]]:
    """
    Scrapes chocolate price information from kupi.cz website.
    Returns both the raw HTML content and structured data parsed by BeautifulSoup.
    """
    url = "https://www.kupi.cz/sleva/cokolada-studentska-pecet-orion"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        product_section = soup.find('strong', string='Čokoláda Studentská pečeť Orion')
        
        if product_section:
            parent_container = product_section.find_parent('div', class_='group_discounts')
            if parent_container:
                parsed_data = parse_with_beautifulsoup(parent_container)
                return str(parent_container), parsed_data
            
        return "Product section not found", []

    except requests.RequestException as e:
        print(f"Error fetching the website: {e}")
        return f"Error: {str(e)}", []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return f"Error: {str(e)}", []

def parse_with_beautifulsoup(container) -> List[Dict]:
    """
    Parses the HTML content using BeautifulSoup to extract detailed discount information.
    """
    discounts = []
    rows = container.find_all('tr', class_='discount_row')
    
    for row in rows:
        try:
            # Shop name
            shop_name_elem = row.find('span', class_='discounts_shop_name')
            shop_name = shop_name_elem.find('span').get_text(strip=True) if shop_name_elem else "N/A"
            
            # Price
            price_elem = row.find('strong', class_='discount_price_value')
            price = price_elem.get_text(strip=True) if price_elem else "N/A"
            
            # Amount (grams)
            amount_elem = row.find('div', class_='discount_amount')
            amount = amount_elem.get_text(strip=True).replace('/', '').strip() if amount_elem else "N/A"
            
            # Expiration
            validity_elem = row.find('td', class_='discounts_validity')
            validity_span = validity_elem.find('span') if validity_elem else None
            expiration = validity_span.get_text(strip=True) if validity_span else "N/A"
            
            # Number of shops
            markets_elem = row.find('div', class_='discounts_markets')
            markets_link = markets_elem.find('a') if markets_elem else None
            shops_valid = markets_link.get_text(strip=True) if markets_link else "N/A"
            
            # Additional note if present
            note_elem = row.find('div', class_='discount_note')
            note = note_elem.get_text(strip=True) if note_elem else ""
            
            discount_info = {
                "shop_name": shop_name,
                "price": price,
                "amount": amount,
                "expiration": expiration,
                "shops_valid": shops_valid,
                "additional_note": note
            }
            
            discounts.append(discount_info)
            
        except Exception as e:
            print(f"Error parsing row: {e}")
            continue
    
    return discounts

def save_results(beautifulsoup_data: List[Dict], filename: str = "initial_results.json"):
    """
    Saves the BeautifulSoup parsed results to a JSON file.
    """
    results = {
        "beautifulsoup_parsing": beautifulsoup_data
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, ensure_ascii=False, indent=2, fp=f)
    
    print(f"Results saved to {filename}")

if __name__ == "__main__":
    # Scrape the website and get both raw HTML and BeautifulSoup parsed data
    raw_html, beautifulsoup_data = scrape_website()
    
    # Save the BeautifulSoup parsed results
    save_results(beautifulsoup_data)
    
    # Print BeautifulSoup results for immediate comparison
    print("\nBeautifulSoup Parsing Results:")
    print(json.dumps(beautifulsoup_data, ensure_ascii=False, indent=2))
