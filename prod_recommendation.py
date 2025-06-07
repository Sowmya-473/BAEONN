from IPython.display import Image, display
import requests
import re
from typing import List, Dict
from bs4 import BeautifulSoup
import logging
import os
from dotenv import load_dotenv
load_dotenv()

# ========== CONFIG ==========
SCRAPINGBEE_API_KEY = "scrapingbee_api_key"
GEMINI_API_KEY = "gemini_api_key"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
SERPAPI_KEY = "serpAPI_key"

# ========== LOGGER ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== GEMINI REASONING ==========
def get_gemini_reasoning(product_title: str, budget: int, profile: dict) -> str:
    prompt = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            f"A {profile['age']} y/o {profile['gender']} {profile['occupation']} from {profile['location']} "
                            f"is buying a {query} under ₹{budget}. Here's the product:\n"
                            f"→ {product_title}\n\n"
                            "Give a **precise and unique one-line reason** (comma-separated, max 15 words) "
                            "that explains why this product is suitable for their needs. "
                            "Avoid repeating phrases used for other tablets. Focus on the **most unique value** of the product "
                            "(e.g. stylus support, Dolby audio, ergonomic design, etc.). No generic phrases like 'good display' or 'long battery life'."
                        )
                    }
                ]
            }
        ]
    }

    response = requests.post(
        GEMINI_URL,
        headers={"Content-Type": "application/json"},
        params={"key": GEMINI_API_KEY},
        json=prompt
    )

    try:
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text'].strip().strip(".")
        else:
            logger.error(f"Gemini API error: {response.status_code} - {response.text}")
            return "No reason available"
    except Exception as e:
        logger.error(f"Gemini exception: {e}")
        return "No reason available"

# ========== SERPAPI PRODUCT LINK ==========
def get_serpapi_link(title):
    from urllib.parse import quote_plus

    params = {
        "engine": "google_shopping",
        "q": title,
        "api_key": SERPAPI_KEY,
        "gl": "IN",
        "hl": "en",
        "google_domain": "google.co.in"
    }
    try:
        response = requests.get("https://serpapi.com/search", params=params)
        if response.status_code == 200:
            results = response.json().get("shopping_results", [])
            if results:
                top_result = results[0]
                return top_result.get("product_link") or top_result.get("link") or "No deal found"
    except Exception as e:
        print(f"❌ SerpAPI error for '{title}': {e}")
    return "No deal found"

# ========== SCRAPING ==========
def fetch_html_scrapingbee(url: str) -> str:
    params = {
        "api_key": SCRAPINGBEE_API_KEY,
        "url": url,
        "render_js": "true"
    }
    response = requests.get("https://app.scrapingbee.com/api/v1/", params=params, timeout=60)
    response.raise_for_status()
    return response.text

def get_flipkart_url(query: str, budget: int) -> str:
    from urllib.parse import quote

    query_encoded = quote(query)
    lower = int(budget * 0.9)
    upper = budget

    base_url = f"https://www.flipkart.com/search?q={query_encoded}&sort=popularity"
    price_filter = f"&p[]=facets.price_range.from%3D{lower}&p[]=facets.price_range.to%3D{upper}"
    return base_url + price_filter

def extract_flipkart_products(html: str) -> List[Dict[str, any]]:
    soup = BeautifulSoup(html, 'html.parser')
    products = []
    product_anchors = soup.find_all('a', class_='CGtC98')

    for anchor in product_anchors:
        title_elem = anchor.find('div', class_='KzDlHZ')
        price_elem = anchor.find('div', class_='Nx9bqj')
        rating_elem = anchor.find('div', class_='XQDdHH')
        img_tag = anchor.find('img')

        title = title_elem.get_text(strip=True) if title_elem else None
        base_title = title.split('(')[0].strip().lower() if title else None
        price_raw = price_elem.get_text(strip=True) if price_elem else None
        price = re.sub(r'[^\d]', '', price_raw) if price_raw else None
        avg_rating = float(rating_elem.get_text(strip=True)) if rating_elem else 0
        image_url = img_tag['src'] if img_tag and img_tag.has_attr('src') else None

        if base_title and price and "refurbished" not in base_title and "renewed" not in base_title:
            if base_title not in {p['title'].split('(')[0].strip().lower() for p in products}:
                products.append({
                    'title': title,
                    'price': int(price),
                    'rating': avg_rating,
                    'source': 'Flipkart',
                    'image': image_url
                })
    return products

def get_amazon_url(query: str, budget: int) -> str:
    encoded_query = query.replace(" ", "+")
    min_price = int(budget * 0.80 * 100)
    max_price = int(budget * 1.10 * 100)
    return f"https://www.amazon.in/s?k={encoded_query}&rh=p_36%3A{min_price}-{max_price}"

def extract_amazon_products(html: str) -> List[Dict[str, any]]:
    soup = BeautifulSoup(html, 'html.parser')
    products = []
    product_tags = soup.select('div.s-main-slot div[data-component-type="s-search-result"]')

    for tag in product_tags:
        title_tag = tag.select_one('h2 span')
        price_tag = tag.select_one('.a-price span.a-offscreen')
        rating_tag = tag.select_one('i span.a-icon-alt')
        img_tag = tag.select_one('img.s-image')

        if not title_tag or not price_tag or not rating_tag:
            continue

        title = title_tag.text.strip()
        base_title = title.split('(')[0].strip().lower()
        price = re.sub(r'[^\d]', '', price_tag.text)
        rating = float(rating_tag.text.split()[0])
        image_url = img_tag['src'] if img_tag and img_tag.has_attr('src') else None

        if "refurbished" in base_title or "renewed" in base_title:
            continue

        if base_title not in {p['title'].split('(')[0].strip().lower() for p in products}:
            products.append({
                'title': title,
                'price': int(price),
                'rating': rating,
                'source': 'Amazon',
                'image': image_url
            })
    return products

# ========== RECOMMEND ==========
def recommend_products(query: str, budget: int, profile: dict):
    print(f"\nSearching for '{query}'...\n")
    try:
        flipkart_html = fetch_html_scrapingbee(get_flipkart_url(query, budget))
        amazon_html = fetch_html_scrapingbee(get_amazon_url(query, budget))

        flipkart_products = extract_flipkart_products(flipkart_html)
        amazon_products = extract_amazon_products(amazon_html)

        all_products = flipkart_products + amazon_products

        unique_titles = set()
        deduped_products = []
        for p in all_products:
            base_title = p['title'].split('(')[0].strip().lower()
            if base_title not in unique_titles:
                unique_titles.add(base_title)
                deduped_products.append(p)

        primary_filtered = [p for p in deduped_products if 4.4 <= p['rating'] <= 5.0 and (budget * 0.9) <= p['price'] <= budget]

        if not primary_filtered:
            fallback_filtered = [p for p in deduped_products if 3.8 <= p['rating'] <= 5.0 and (budget * 0.85) <= p['price'] <= (budget * 1.1)]
            filtered = sorted(fallback_filtered, key=lambda x: x['rating'], reverse=True)[:5]
        else:
            filtered = sorted(primary_filtered, key=lambda x: x['rating'], reverse=True)[:5]

        top_products = sorted(filtered, key=lambda x: x['rating'], reverse=True)[:5]
        print("\nTop Recommended Products:\n")
        for i, product in enumerate(top_products, 1):
            short_title = product['title'].split(",")[0]
            reason = get_gemini_reasoning(short_title, budget, profile)
            price_str = f"₹{product['price']}"
            rating = product['rating']
            source = product['source']
            image_url = product['image']
            product_link = get_serpapi_link(short_title)

            print(f"{i}. {short_title}")
            print(f"   Reason: {reason}")
            print(f"   Check it out: {product_link}\n")

            if image_url:
                display(Image(url=image_url))

    except Exception as e:
        print(f"Error: {e}")

# ========== MAIN ==========
if __name__ == "__main__":
    query = input("Enter the product name: ").strip()
    budget = int(input("Enter your budget (INR): ").strip())
    profile = {
        "age": input("Age: ").strip(),
        "occupation": input("Occupation: ").strip(),
        "gender": input("Gender: ").strip(),
        "location": input("Location: ").strip()
    }
    recommend_products(query, budget, profile)
