

import sqlite3
from datetime import datetime, timedelta
import random

def generate_test_data():
    """Generate artificial product data with price history over the last 30 days"""
    # Test products
    products = [
        {
            'url': 'https://www.kupi.cz/sleva/tunak-v-oleji-rio-mare',
            'name': 'Tuňák v oleji Rio Mare',
            'base_price': 89.90,
            'amount': '160g'
        },
        {
            'url': 'https://www.kupi.cz/sleva/cokolada-studentska-pecet-orion',
            'name': 'Čokoláda Studentská pečeť',
            'base_price': 39.90,
            'amount': '180g'
        }
    ]
    
    # Shops with their typical discount patterns
    shops = [
        {'name': 'Albert', 'discount_range': (0.7, 0.85)},
        {'name': 'Kaufland', 'discount_range': (0.75, 0.9)},
        {'name': 'Tesco', 'discount_range': (0.8, 0.95)}
    ]
    
    conn = sqlite3.connect('price_tracker.db')
    c = conn.cursor()
    
    # Clear existing test data (optional)
    c.execute('DELETE FROM price_history')
    c.execute('DELETE FROM products')
    conn.commit()
    
    # Generate 30 days of price history
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    for product in products:
        # Insert product
        c.execute('''
            INSERT INTO products (url, name)
            VALUES (?, ?)
        ''', (product['url'], product['name']))
        product_id = c.lastrowid
        
        # Generate price history
        current_date = start_date
        while current_date <= end_date:
            # Each shop might or might not have a discount on any given day
            for shop in shops:
                if random.random() < 0.3:  # 30% chance of having a discount
                    discount_factor = random.uniform(*shop['discount_range'])
                    discounted_price = round(product['base_price'] * discount_factor, 2)
                    
                    # Calculate price per gram
                    amount_value = float(product['amount'].replace('g', ''))
                    price_per_gram = round(discounted_price / amount_value, 3)
                    
                    # Random expiration date between 3-7 days from current date
                    expiration_date = (current_date + timedelta(days=random.randint(3, 7))).strftime('%Y-%m-%d')
                    
                    c.execute('''
                        INSERT INTO price_history 
                        (product_id, shop_name, price, amount, price_per_gram, 
                         expiration, shops_valid, additional_note, fetch_timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        product_id,
                        shop['name'],
                        discounted_price,
                        product['amount'],
                        price_per_gram,
                        f"Platí do {expiration_date}",
                        "Všechny prodejny",
                        f"Sleva {int((1-discount_factor)*100)}%",
                        current_date.isoformat()
                    ))
            
            current_date += timedelta(days=1)
    
    conn.commit()
    conn.close()

def verify_database():
    """Verify that test data was properly inserted"""
    conn = sqlite3.connect('price_tracker.db')
    c = conn.cursor()
    
    print("\n=== Database Verification ===")
    
    # Check products
    c.execute('SELECT id, name, url FROM products')
    products = c.fetchall()
    print(f"\nProducts in database: {len(products)}")
    for product in products:
        print(f"- {product[1]}")
        
        # Check price history for each product
        c.execute('''
            SELECT COUNT(*), MIN(price), MAX(price), COUNT(DISTINCT date(fetch_timestamp))
            FROM price_history
            WHERE product_id = ?
        ''', (product[0],))
        stats = c.fetchone()
        print(f"  * Total price records: {stats[0]}")
        print(f"  * Price range: {stats[1]:.2f} - {stats[2]:.2f} Kč")
        print(f"  * Days with data: {stats[3]}")
        
        # Sample of recent prices
        c.execute('''
            SELECT date(fetch_timestamp) as date,
                   GROUP_CONCAT(shop_name) as shops,
                   GROUP_CONCAT(price) as prices
            FROM price_history
            WHERE product_id = ?
            GROUP BY date(fetch_timestamp)
            ORDER BY date(fetch_timestamp) DESC
            LIMIT 3
        ''', (product[0],))
        recent = c.fetchall()
        print("  * Recent price history:")
        for day in recent:
            print(f"    {day[0]}: {day[1]} -> {day[2]} Kč")
            
    conn.close()

if __name__ == '__main__':
    print("Generating test data...")
    generate_test_data()
    verify_database()