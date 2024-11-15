

import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, List, Optional, Tuple
import json
import os
from openai import OpenAI

def scrape_website() -> Tuple[str, List[Dict]]:
    """
    Scrapes chocolate price information from kupi.cz website.
    Returns both the raw HTML content and structured data parsed by BeautifulSoup.
    """
    url = "https://www.kupi.cz/slevy/tabulkove-cokolady"
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

def create_style_assistant():
    client = OpenAI(
        api_key='xai-WgB5KTpM3RuRzQl97ysCrpGxo7Lmev6z0vYOzvpO3B2jtziddh5ExhtQl2LMf0FKMEjQnwAylmzLYGS3',
        base_url="https://api.x.ai/v1",
    )
    return client

def generate_response(client, prompt):
    completion = client.chat.completions.create(
        model="grok-beta",
        messages=[
            {"role": "system", "content": "You are best programmer in the world"},
            {"role": "user", "content": prompt},
        ],
    )
    return completion.choices[0].message.content

def save_results(beautifulsoup_data: List[Dict], ai_response: str, filename: str = "comparison_results.json"):
    """
    Saves both BeautifulSoup and AI results to a JSON file for comparison.
    """
    results = {
        "beautifulsoup_parsing": beautifulsoup_data,
        "ai_response": ai_response
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, ensure_ascii=False, indent=2, fp=f)
    
    print(f"Results saved to {filename}")

if __name__ == "__main__":
    # Scrape the website and get both raw HTML and BeautifulSoup parsed data
    raw_html, beautifulsoup_data = scrape_website()
    
    # Create the AI assistant
    client = create_style_assistant()
    
    # Generate AI response
    prompt = (
        "Find prices of Čokoláda Studentská pečeť Orion in all shops and provide me with json that will have "
        "all offering and each will have shop name, price, grams, expiration day of discount and for how many "
        f"shops its valid found under for example 'plati pro 2 nejblizssi pobocky' content of the website is following: {raw_html}"
    )
    ai_response = generate_response(client, prompt)
    
    # Save both results for comparison
    save_results(beautifulsoup_data, ai_response)
    
    # Print both results for immediate comparison
    print("\nBeautifulSoup Parsing Results:")
    print(json.dumps(beautifulsoup_data, ensure_ascii=False, indent=2))
    
    print("\nAI Analysis Results:")
    print(ai_response)