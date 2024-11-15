# app.py
from flask import Flask, render_template, jsonify
import sqlite3
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from scraper import scrape_all_products  # Import your scraping function
import logging
import atexit

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_product_data():
    """Get latest product data from database"""
    conn = sqlite3.connect('price_tracker.db')
    c = conn.cursor()
    
    products_data = []
    c.execute('SELECT id, name, url FROM products')
    for product_id, product_name, product_url in c.fetchall():
        c.execute('''
            SELECT shop_name, price, amount, price_per_gram, expiration, shops_valid, 
                    additional_note, fetch_timestamp
            FROM price_history
            WHERE product_id = ? AND fetch_timestamp = (
                SELECT MAX(fetch_timestamp) FROM price_history WHERE product_id = ?
            )
            ORDER BY price_per_gram ASC
            LIMIT 3
        ''', (product_id, product_id))
        
        deals = [{
            'shop_name': row[0],
            'price': row[1],
            'amount': row[2],
            'price_per_gram': row[3],
            'expiration': row[4],
            'shops_valid': row[5],
            'additional_note': row[6],
            'fetch_timestamp': row[7]
        } for row in c.fetchall()]
        
        products_data.append({
            'id': product_id,
            'name': product_name,
            'url': product_url,
            'deals': deals
        })
    
    conn.close()
    return products_data

def get_price_history(product_id):
    """Get price history for a specific product"""
    conn = sqlite3.connect('price_tracker.db')
    c = conn.cursor()
    
    # Get product details
    c.execute('SELECT name, url FROM products WHERE id = ?', (product_id,))
    product_name, product_url = c.fetchone()
    
    # Get price history - lowest price per day
    c.execute('''
        SELECT 
            date(fetch_timestamp) as date,
            MIN(price) as lowest_price,
            GROUP_CONCAT(shop_name) as shops
        FROM price_history
        WHERE product_id = ?
        GROUP BY date(fetch_timestamp)
        ORDER BY date
    ''', (product_id,))
    
    history = [{
        'date': row[0],
        'price': row[1],
        'shops': row[2].split(',')[0]  # Take first shop name for simplicity
    } for row in c.fetchall()]
    
    conn.close()
    return {
        'name': product_name,
        'url': product_url,
        'history': history
    }

def scrape_job():
    """Function to be scheduled for scraping"""
    try:
        logger.info("Starting scheduled scraping job")
        scrape_all_products()
        logger.info("Completed scheduled scraping job")
    except Exception as e:
        logger.error(f"Error in scheduled scraping job: {str(e)}")

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=scrape_job, 
                 trigger="interval", 
                 days=2,
                 id='scraping_job',
                 name='Scrape product prices every 2 days')

# Start the scheduler
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

@app.route('/')
def index():
    products = get_product_data()
    return render_template('index.html', products=products)

@app.route('/product/<int:product_id>/history')
def product_history(product_id):
    history_data = get_price_history(product_id)
    return render_template('price_history.html', product=history_data)

if __name__ == '__main__':
    # Run initial scrape when starting the app (optional)
    try:
        logger.info("Running initial scrape on startup")
        scrape_job()
    except Exception as e:
        logger.error(f"Error in initial scrape: {str(e)}")
    
    app.run(debug=True)