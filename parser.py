import requests
from bs4 import BeautifulSoup
import csv
import re
import json

LOGIN_URL = "https://pro.ekt.kz/auth/"
CATALOG_URL = "https://pro.ekt.kz/catalog/kabel_provod/"
BASE_URL = "https://pro.ekt.kz"

LOGIN = "info@electrotech.kz"
PASSWORD = "RtnM91jK."

def login():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    })

    try:
        response = session.get(LOGIN_URL)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error getting login page: {e}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')

    sessid = None
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string and 'bitrix_sessid' in script.string:
            match = re.search(r'bitrix_sessid":"(.*?)"', script.string)
            if match:
                sessid = match.group(1)
                break

    if not sessid:
        print("Could not find bitrix_sessid.")
        return None

    login_data = {
        'USER_LOGIN': LOGIN,
        'USER_PASSWORD': PASSWORD,
        'backurl': '/',
        'AUTH_FORM': 'Y',
        'TYPE': 'AUTH',
        'Login': 'Войти',
        'sessid': sessid
    }

    try:
        login_post_url = "https://pro.ekt.kz/auth/?login=yes"
        response = session.post(login_post_url, data=login_data)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error on login request: {e}")
        if e.response is not None:
            print(e.response.text)
        return None

    if "Личный кабинет" in response.text:
        print("Login successful!")
        return session
    else:
        print("Login failed.")
        print(response.text)
        return None

def parse_products(session):
    all_products = []

    category_urls = [
        "https://pro.ekt.kz/catalog/kabel_provod/",
        "https://pro.ekt.kz/catalog/svetilniki_lampy/"
    ]

    for url in category_urls:
        try:
            print(f"Fetching products from: {url}")
            response = session.get(url)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error getting catalog page {url}: {e}")
            continue

        soup = BeautifulSoup(response.content, 'html.parser')

        scripts = soup.find_all('script')
        data_str = None
        for script in scripts:
            if script.string and 'new B2BPortal.Components.CatalogSection' in script.string:
                data_str = script.string
                break

        if not data_str:
            print(f"Could not find product data script on page {url}")
            continue

        match = re.search(r'items: (\[.*?\]),\s*pagination:', data_str, re.DOTALL)
        if not match:
            # Fallback for slightly different structure
            match = re.search(r'items: (\[.*?\])\s*,\s*headers:', data_str, re.DOTALL)
        if not match:
            print(f"Could not extract items from script on page {url}")
            continue

        items_str = match.group(1)

        # This is a bit of a hack to make the JS object string into valid JSON
        try:
            # Replace single quotes with double quotes, being careful not to mess up quotes within strings
            items_str = re.sub(r"'", '"', items_str)
            # Add quotes around unquoted keys
            items_str = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', items_str)

            items = json.loads(items_str)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON on page {url}: {e}")
            # print("Problematic JSON string:", items_str)
            continue

        for item in items:
            product_id = item.get('id')
            product_info = item.get('products', {}).get(str(product_id)) # ID can be int or string
            if not product_info:
                 # Try with int key if string key fails
                product_info = item.get('products', {}).get(int(product_id))
                if not product_info:
                    continue

            name = product_info.get('name', 'N/A').strip()
            url = BASE_URL + item.get('url', '')

            price_info = product_info.get('prices', {}).get('ZERO-INF', {})
            price = price_info.get('catalog_price_scale_5_num', 'N/A')

            all_products.append({
                'name': name,
                'price': price,
                'url': url
            })

    print(f"Total products parsed: {len(all_products)}")
    return all_products

def save_to_csv(products):
    if not products:
        print("No products to save.")
        return

    filename = 'products.csv'
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['name', 'price', 'url']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for product in products:
            writer.writerow(product)

    print(f"Saved {len(products)} products to {filename}")


def main():
    print("Parser script started.")
    session = login()
    if session:
        products = parse_products(session)
        if products:
            save_to_csv(products)

if __name__ == "__main__":
    main()
