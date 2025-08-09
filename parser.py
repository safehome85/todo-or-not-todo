import requests
from bs4 import BeautifulSoup
import csv
import re
import json
from urllib.parse import urljoin
import math

LOGIN_URL = "https://pro.ekt.kz/auth/"
CATALOG_URL = "https://pro.ekt.kz/catalog/"
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

def get_category_urls(session):
    print(f"Fetching main catalog page to find categories: {CATALOG_URL}")
    try:
        response = session.get(CATALOG_URL)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error getting main catalog page: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    category_urls = []

    category_cards = soup.select('div.col-xl-4 div.kt-portlet__body h4 a')
    for card_link in category_cards:
        if card_link.has_attr('href'):
            url = urljoin(BASE_URL, card_link['href'])
            category_urls.append(url)

    print(f"Found {len(category_urls)} main categories.")
    return category_urls

def parse_products_from_page(soup, all_products):
    scripts = soup.find_all('script')
    data_str = None
    for script in scripts:
        if script.string and 'new B2BPortal.Components.CatalogSection' in script.string:
            data_str = script.string
            break

    if not data_str:
        return None

    items_match = re.search(r'items: (\[.*?\]),\s*(?:pagination|headers):', data_str, re.DOTALL)
    if not items_match:
        return None

    items_str = items_match.group(1)
    try:
        # This is a simplified way to handle non-standard JSON, it might not be perfect.
        items_str = items_str.replace("'", '"')
        items_str = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', items_str)
        items = json.loads(items_str)
    except json.JSONDecodeError as e:
        return None

    for item in items:
        product_id = item.get('id')
        product_info = item.get('products', {}).get(str(product_id))
        if not product_info:
            product_info = item.get('products', {}).get(int(product_id))
            if not product_info:
                continue

        name = product_info.get('name', 'N/A').strip()
        url = urljoin(BASE_URL, item.get('url', ''))

        price_info = product_info.get('prices', {}).get('ZERO-INF', {})
        if not isinstance(price_info, dict):
            price = "N/A"
        else:
            price = price_info.get('catalog_price_scale_5_num', 'N/A')

        all_products.append({'name': name, 'price': price, 'url': url})

    pagination_match = re.search(r'pagination: (\{.*?\})', data_str, re.DOTALL)
    if not pagination_match:
        return None

    pagination_str = pagination_match.group(1)
    try:
        pagination_str = pagination_str.replace("'", '"')
        pagination_str = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', pagination_str)
        pagination_info = json.loads(pagination_str)
    except json.JSONDecodeError:
        return None

    return pagination_info

def parse_category_recursively(session, url, all_products):
    print(f"Parsing category: {url}")
    try:
        response = session.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error getting page {url}: {e}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')

    sub_category_links = soup.select('div.col-xl-4 div.kt-portlet__body h4 a')
    if sub_category_links:
        print(f"Found {len(sub_category_links)} sub-categories on {url}")
        for link in sub_category_links:
            if link.has_attr('href'):
                sub_url = urljoin(BASE_URL, link['href'])
                parse_category_recursively(session, sub_url, all_products)
    else:
        print(f"No sub-categories found on {url}, parsing for products.")
        pagination_info = parse_products_from_page(soup, all_products)

        if pagination_info and pagination_info.get('hide') == 'N':
            total_records = int(pagination_info.get('totalRecords', 0))
            per_page = int(pagination_info.get('perPage', 10))
            if per_page > 0:
                total_pages = math.ceil(total_records / per_page)
                page_param = pagination_info.get('navName', 'PAGEN_1')

                print(f"Found {total_pages} pages for {url}")

                for page_num in range(2, total_pages + 1):
                    separator = '&' if '?' in url else '?'
                    page_url = f"{url}{separator}{page_param}={page_num}"
                    print(f"Parsing page {page_num} of {total_pages}: {page_url}")
                    try:
                        next_page_response = session.get(page_url)
                        next_page_response.raise_for_status()
                        next_page_soup = BeautifulSoup(next_page_response.content, 'html.parser')
                        parse_products_from_page(next_page_soup, all_products)
                    except requests.exceptions.RequestException as e:
                        print(f"Error getting page {page_url}: {e}")
                        continue

def save_to_csv(products):
    if not products:
        print("No products to save.")
        return

    filename = 'products.csv'
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['name', 'price', 'url']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(products)

    print(f"Saved {len(products)} products to {filename}")

def main():
    """
    Main function to run the parser.
    Note: A full crawl of the site is time-consuming and may time out in some environments.
    """
    print("Parser script started.")
    session = login()
    if session:
        main_category_urls = get_category_urls(session)
        all_products = []
        if main_category_urls:
            # Loop through all main categories and parse them recursively
            for category_url in main_category_urls:
                parse_category_recursively(session, category_url, all_products)

        print(f"\nTotal products parsed: {len(all_products)}")
        save_to_csv(all_products)

if __name__ == "__main__":
    main()
