import requests
from bs4 import BeautifulSoup
import math
import time
import urllib.parse

# ======= CONFIG =======
SCRAPINGBEE_API_KEY = 'PO7HX1AE9RP0HJB2RY1BC65FDFP62PO14EZ0OJQU606YYXDEI1UZWC3NWP3PM0QYV8838KGEQQX989XM'  # 🔁 Replace with your actual key
HEADERS = {'User-Agent': 'Mozilla/5.0'}
BASE_URL = "https://app.scrapingbee.com/api/v1/"

# ======= USER INPUT =======
query = input("Enter the product you want to search on Amazon.in: ").strip()
encoded_query = urllib.parse.quote_plus(query)
search_url = f'https://www.amazon.in/s?k={encoded_query}'

# ======= FETCH AMAZON SEARCH PAGE =======
params = {
    'api_key': SCRAPINGBEE_API_KEY,
    'url': search_url,
    'render_js': 'true',
    'wait': '5000'
}

response = requests.get(BASE_URL, params=params, headers=HEADERS)
soup = BeautifulSoup(response.text, 'html.parser')
products = soup.select('div.s-main-slot div[data-component-type="s-search-result"]')

results = []

for i, product in enumerate(products[:10]):  # Top 10 only
    title_tag = product.select_one('h2 span')
    price_tag = product.select_one('.a-price span.a-offscreen')
    rating_tag = product.select_one('i span.a-icon-alt')
    rating_count_tag = product.select_one('span.a-size-base.s-underline-text')
    link_tag = product.select_one('a.a-link-normal.s-no-outline')

    title = title_tag.text.strip() if title_tag else 'N/A'
    price_str = price_tag.text.strip().replace('₹', '').replace(',', '') if price_tag else '0'
    rating_str = rating_tag.text.strip().split(' ')[0] if rating_tag else '0'
    rating_count_str = rating_count_tag.text.strip().replace(',', '') if rating_count_tag else '0'
    product_link = f"https://www.amazon.in{link_tag['href']}" if link_tag and link_tag.get('href') else 'N/A'

    try:
        price = float(price_str)
        rating = float(rating_str)
        rating_count = int(rating_count_str)
    except:
        price, rating, rating_count = 0, 0, 0

    # Calculate Rank Score
    try:
        if price > 0 and rating > 0:
            score = (rating / 5.0) * math.log10(rating_count + 1) * (1 / math.sqrt(price))
        else:
            score = 0
    except:
        score = 0

    results.append({
        'title': title,
        'price': f"₹{price:,.0f}" if price > 0 else 'N/A',
        'rating': f"{rating:.1f}",
        'ratings': f"{rating_count:,}",
        'score': score,
        'link': product_link
    })

# ======= SORT AND DISPLAY =======
sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)

for idx, item in enumerate(sorted_results, 1):
    print(f"{idx}. {item['title']}")
    print(f"   Price: {item['price']}")
    print(f"   Rating: {item['rating']} out of 5 stars")
    print(f"   Ratings: {item['ratings']}")
    print(f"   Link: {item['link']}\n")
