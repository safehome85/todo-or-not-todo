import requests
from bs4 import BeautifulSoup
import csv
import re
import json
from urllib.parse import urljoin
import math
import os

LOGIN_URL = "https://pro.ekt.kz/auth/"
CATALOG_URL = "https://pro.ekt.kz/catalog/"
BASE_URL = "https://pro.ekt.kz"

LOGIN = "info@electrotech.kz"
PASSWORD = "RtnM91jK."

# Имя файла для сохранения
CSV_FILENAME = 'products1.csv'
# Поля для CSV файла
CSV_FIELDNAMES = [
    'Название', 'Цена', 'Розница', 'Категория', 'Артикул',
    'Описание', 'Характеристики', 'Количество', 'Изображение'
]

def login():
    """Аутентификация на сайте и возврат объекта сессии."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    })

    try:
        response = session.get(LOGIN_URL)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Ошибка получения страницы входа: {e}")
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
        print("Не удалось найти 'bitrix_sessid' в JavaScript на странице.")
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
        response = session.post(login_post_url, data=login_data, allow_redirects=True)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе на вход: {e}")
        return None

    if "Личный кабинет" in response.text:
        print("Вход выполнен успешно!")
        return session
    else:
        print("Вход не удался.")
        return None

def get_category_urls(session):
    """Получение URL-адресов основных категорий с главной страницы каталога."""
    print(f"Получение ссылок на основные категории: {CATALOG_URL}")
    try:
        response = session.get(CATALOG_URL)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Ошибка получения главной страницы каталога: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    category_urls = []

    category_cards = soup.select('div.col-xl-4 div.kt-portlet__body h4 a')
    for card_link in category_cards:
        if card_link.has_attr('href'):
            url = urljoin(BASE_URL, card_link['href'])
            category_urls.append(url)

    print(f"Найдено {len(category_urls)} основных категорий.")
    return category_urls

def create_csv_file(filename, fieldnames):
    """Создает CSV-файл и записывает в него заголовки."""
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
    print(f"Создан файл '{filename}' с заголовками.")

def append_to_csv(filename, fieldnames, data_dict):
    """Добавляет одну строку данных в CSV-файл."""
    try:
        with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writerow(data_dict)
    except IOError as e:
        print(f"Ошибка записи в файл '{filename}': {e}")

def format_specs_as_html(specs_string):
    """
    Преобразует строку характеристик, разделенную точкой с запятой,
    в HTML-код в виде маркированного списка.
    """
    if not specs_string or specs_string.strip() in ('N/A', ''):
        return ''

    html_list = ['<ul class="product-specs">']
    characteristics = specs_string.split('; ')

    for item in characteristics:
        parts = item.split(': ', 1)
        if len(parts) == 2:
            key, value = parts[0].strip(), parts[1].strip()
            html_list.append(f'    <li><strong>{key}:</strong> {value}</li>')

    html_list.append('</ul>')
    return '\n'.join(html_list)

def parse_product_details(session, product_url):
    """Парсинг детальной информации со страницы одного товара."""
    try:
        response = session.get(product_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
    except requests.exceptions.RequestException as e:
        print(f"  -> Ошибка при получении страницы товара {product_url}: {e}")
        return {}

    sku_element = soup.select_one('div.catalog_detail__row__block__articul span')
    sku = sku_element.get_text(strip=True) if sku_element else 'N/A'

    img_element = soup.select_one('img.catalog_detail__row__picture__img')
    image_url = urljoin(BASE_URL, img_element['src']) if img_element and img_element.has_attr('src') else 'N/A'

    stock_element = soup.select_one('div.catalog_detail__row__block__store__stock__value')
    stock = '0'
    if stock_element:
        full_stock_text = stock_element.get_text(separator=' ', strip=True)
        match = re.search(r'\d+', full_stock_text)
        if match:
            stock = match.group(0)

    desc_container = soup.select_one('div[tab="description"] .catalog_detail__tabs__body__item__value')
    description = desc_container.get_text(separator="\n", strip=True) if desc_container else 'N/A'

    specs_dict = {}
    spec_items = soup.select('div.catalog_detail__tabs__body__chars_item')
    for item in spec_items:
        title_el = item.select_one('.catalog_detail__tabs__body__chars_item__title')
        value_el = item.select_one('.catalog_detail__tabs__body__chars_item__value')
        if title_el and value_el:
            specs_dict[title_el.get_text(strip=True)] = value_el.get_text(strip=True)
    specifications = "; ".join([f"{k}: {v}" for k, v in specs_dict.items()])

    breadcrumbs_container = soup.select_one('div.kt-subheader__breadcrumbs')
    breadcrumbs = ''
    if breadcrumbs_container:
        path_elements = breadcrumbs_container.select('a.kt-subheader__breadcrumbs-link')
        path_texts = [elem.get_text(strip=True) for elem in path_elements if elem.get_text(strip=True)]

        if len(path_texts) > 3:
            sliced_path = path_texts[2:-1]
            breadcrumbs = ">".join(sliced_path)
        elif len(path_texts) > 2:
            sliced_path = path_texts[2:]
            breadcrumbs = ">".join(sliced_path)

    return {
        'sku': sku, 'image_url': image_url, 'stock': stock,
        'description': description, 'specifications': specifications,
        'breadcrumbs': breadcrumbs
    }

def parse_products_from_page(session, soup, product_counter, processed_names):
    """Извлечение данных о товарах, запись в файл и обработка пагинации."""
    scripts = soup.find_all('script')
    data_str = None
    for script in scripts:
        if script.string and 'new B2BPortal.Components.CatalogSection' in script.string:
            data_str = script.string
            break
    if not data_str: return None

    items_match = re.search(r'items:\s*(\[.*?\]),\s*(?:pagination|headers):', data_str, re.DOTALL)
    if not items_match: return None

    items_str = items_match.group(1).replace("'", '"')
    items_str = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', items_str)
    try:
        items = json.loads(items_str)
    except json.JSONDecodeError: return None

    for item in items:
        product_id = item.get('id')
        product_info = item.get('products', {}).get(str(product_id))
        if not product_info: continue

        name = product_info.get('name', 'N/A').strip()
        price_info = product_info.get('prices', {}).get('ZERO-INF', {})

        if name in processed_names:
            print(f"  -> Пропуск дубликата: {name}")
            continue

        url = urljoin(BASE_URL, item.get('url', ''))
        price = price_info.get('catalog_price_scale_30_num', 'N/A') if isinstance(price_info, dict) else "N/A"

        print(f"  -> Получение деталей для: {name}")
        details = parse_product_details(session, url)

        internal_data = {'name': name, 'price': price, **details}

        base_price = internal_data.get('price', 'N/A')
        retail_price = 'N/A'
        try:
            price_float = float(base_price)
            calculated_price = price_float * 1.15
            retail_price = int(math.ceil(calculated_price / 10.0)) * 10
        except (ValueError, TypeError):
            pass

        specs_string = internal_data.get('specifications', 'N/A')
        specs_html = format_specs_as_html(specs_string)

        csv_row = {
            'Название': internal_data.get('name', 'N/A'),
            'Цена': base_price,
            'Розница': retail_price,
            'Категория': internal_data.get('breadcrumbs', 'N/A'),
            'Артикул': internal_data.get('sku', 'N/A'),
            'Описание': internal_data.get('description', 'N/A'),
            'Характеристики': specs_html,
            'Количество': internal_data.get('stock', 'N/A'),
            'Изображение': internal_data.get('image_url', 'N/A')
        }

        append_to_csv(CSV_FILENAME, CSV_FIELDNAMES, csv_row)

        processed_names.add(name)
        product_counter['count'] += 1
        print(f"Сохранено товаров: {product_counter['count']}")

    pagination_match = re.search(r'pagination:\s*(\{.*?\})', data_str, re.DOTALL)
    if not pagination_match: return None

    pagination_str = pagination_match.group(1).replace("'", '"')
    pagination_str = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', pagination_str)
    try:
        return json.loads(pagination_str)
    except json.JSONDecodeError:
        return None

def parse_category_recursively(session, url, product_counter, processed_names):
    """Рекурсивный обход категорий и страниц с товарами."""
    print(f"Парсинг категории: {url}")
    try:
        response = session.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Ошибка получения страницы {url}: {e}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')

    sub_category_links = soup.select('div.col-xl-4 div.kt-portlet__body h4 a')
    if sub_category_links:
        print(f"Найдено {len(sub_category_links)} подкатегорий на {url}")
        for link in sub_category_links:
            if link.has_attr('href'):
                sub_url = urljoin(BASE_URL, link['href'])
                parse_category_recursively(session, sub_url, product_counter, processed_names)
    else:
        print(f"Подкатегории не найдены, парсинг товаров на {url}.")
        pagination_info = parse_products_from_page(session, soup, product_counter, processed_names)

        if pagination_info and pagination_info.get('hide') == 'N':
            total_records = int(pagination_info.get('totalRecords', 0))
            per_page = int(pagination_info.get('perPage', 10))
            if per_page > 0:
                total_pages = math.ceil(total_records / per_page)
                print(f"Найдено {total_pages} страниц для {url}")

                if total_pages > 1:
                    page_param = pagination_info.get('navName', 'PAGEN_1')
                    for page_num in range(2, total_pages + 1):
                        separator = '&' if '?' in url else '?'
                        page_url = f"{url}{separator}{page_param}={page_num}"
                        print(f"Парсинг страницы {page_num} из {total_pages}: {page_url}")
                        try:
                            next_page_response = session.get(page_url)
                            next_page_response.raise_for_status()
                            next_page_soup = BeautifulSoup(next_page_response.content, 'html.parser')
                            parse_products_from_page(session, next_page_soup, product_counter, processed_names)
                        except requests.exceptions.RequestException as e:
                            print(f"Ошибка получения страницы {page_url}: {e}")

def main():
    """Основная функция для запуска парсера."""
    print("Запуск скрипта парсера.")

    create_csv_file(CSV_FILENAME, CSV_FIELDNAMES)

    session = login()
    if session:
        main_category_urls = get_category_urls(session)

        product_counter = {'count': 0}
        processed_names = set()

        if main_category_urls:
            for category_url in main_category_urls:
                parse_category_recursively(session, category_url, product_counter, processed_names)

        print(f"\nРабота завершена. Всего сохранено товаров: {product_counter['count']}")
        print(f"Данные сохранены в файл: {CSV_FILENAME}")

if __name__ == "__main__":
    main()
