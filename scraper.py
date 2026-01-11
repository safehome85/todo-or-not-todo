import re
import time
import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError

def get_price_value(price_text):
    if not price_text:
        return float('inf')
    clean_text = re.sub(r'[^\d]', '', price_text)
    if not clean_text:
        return float('inf')
    return int(clean_text)

def scrape_algritravel():
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Use a large viewport to minimize scroll issues
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        page.set_default_timeout(15000)

        print("Navigating...")
        try:
            page.goto("https://algritravel.kz/", timeout=60000)
        except:
            print("Page load timeout.")

        try:
            page.wait_for_selector(".TVCountryFilter", timeout=30000)
        except:
            print("Widget not found.")
            browser.close()
            return

        # 1. Get Countries (Dynamic Extraction with Fallback)
        print("Extracting countries...")
        extracted_countries = []
        try:
            # Force click the dropdown to trigger loading
            page.click(".TVCountryFilter .TVMainSelect", force=True)
            time.sleep(2)

            extracted_countries = page.evaluate("""() => {
                const els = document.querySelectorAll('.TVCountryCheckboxList .TVCheckBox');
                return Array.from(els).map(el => el.innerText.trim()).filter(t => t.length > 0);
            }""")

            # Close it back
            page.mouse.click(0, 0)
            time.sleep(1)

        except Exception as e:
            print(f"Extraction failed: {e}")

        if extracted_countries:
            countries = sorted(list(set(extracted_countries)))
            print(f"Extracted {len(countries)} countries.")
        else:
            print("Using fallback country list.")
            countries = [
                'Турция', 'Египет', 'Таиланд', 'ОАЭ', 'Китай', 'Вьетнам', 'Венгрия',
                'Грузия', 'Индия', 'Индонезия', 'Испания', 'Италия', 'Катар',
                'Киргизия', 'Малайзия', 'Мальдивы', 'Узбекистан', 'Шри-Ланка'
            ]

        # 2. Iterate
        for i, country in enumerate(countries):
            print(f"\n[{i+1}/{len(countries)}] --- {country} ---")

            try:
                # 2.1 Select Country
                # Force open
                page.click(".TVCountryFilter .TVMainSelect", force=True)
                time.sleep(1)

                # JS Click
                clicked = page.evaluate(f"""(name) => {{
                    const items = document.querySelectorAll('.TVCountryCheckboxList .TVCheckBox');
                    for (let item of items) {{
                        if (item.innerText.includes(name)) {{
                            item.click();
                            return true;
                        }}
                    }}
                    return false;
                }}""", country)

                if not clicked:
                    print(f"Could not select {country}")
                    page.mouse.click(0, 0)
                    continue

                time.sleep(2) # Wait for update

                # 2.2 Calendar Scan (12 Months)
                print("Scanning calendar (12 months)...")
                page.click(".TVFlyDatesFilter .TVMainSelect", force=True)
                time.sleep(2)

                min_price = float('inf')
                best_date_text = None
                best_month_offset = 0

                if page.is_visible(".TVCalendar:not(.TVHide)"):
                    # Loop 12 months
                    for month_idx in range(12):
                        # Wait for prices
                        for _ in range(5):
                            count = page.evaluate("document.querySelectorAll('.TVCalendarFlyAvailableCell:not(.TVDisabled) .TVCalendarFlyAvailablePrice').length")
                            if count > 0: break
                            time.sleep(0.5)

                        # Scrape current view
                        current_data = page.evaluate("""() => {
                            const cells = document.querySelectorAll('.TVCalendarFlyAvailableCell:not(.TVDisabled)');
                            return Array.from(cells).map(c => {
                                const p = c.querySelector('.TVCalendarFlyAvailablePrice');
                                const d = c.querySelector('.TVCalendarFlyAvailableDate');
                                return {
                                    price: p ? p.innerText : '',
                                    date: d ? d.innerText : ''
                                };
                            });
                        }""")

                        for item in current_data:
                            val = get_price_value(item['price'])
                            if val < min_price:
                                min_price = val
                                best_date_text = item['date']
                                best_month_offset = month_idx # Record which month (0-11) we found it in

                        # Click Next Month
                        if month_idx < 11:
                            next_btn = page.query_selector(".TVCalendarSliderViewRightButton")
                            # Check disabled
                            if next_btn and "TVDisabled" not in (next_btn.get_attribute("class") or ""):
                                next_btn.click()
                                time.sleep(0.5)
                            else:
                                break # End of calendar

                    print(f"Cheapest: {min_price} on {best_date_text} (Month +{best_month_offset})")

                    if best_date_text and min_price != float('inf'):
                        # Navigate to the best date
                        # 1. Reset to start
                        while True:
                            prev = page.query_selector(".TVCalendarSliderViewLeftButton")
                            if prev and "TVDisabled" not in (prev.get_attribute("class") or ""):
                                prev.click()
                                time.sleep(0.2)
                            else:
                                break

                        # 2. Go forward to the specific month
                        for _ in range(best_month_offset):
                            page.click(".TVCalendarSliderViewRightButton")
                            time.sleep(0.2)

                        # 3. Click the day
                        page.evaluate(f"""(tgt) => {{
                             const cells = document.querySelectorAll('.TVCalendarFlyAvailableCell:not(.TVDisabled)');
                             for (let c of cells) {{
                                 const d = c.querySelector('.TVCalendarFlyAvailableDate');
                                 // Normalized comparison for safety
                                 if (d && d.innerText.trim().replace(/\\s+/g, ' ') == tgt.trim().replace(/\\s+/g, ' ')) {{
                                     c.click();
                                     return;
                                 }}
                             }}
                        }}""", best_date_text)
                        time.sleep(1)
                    else:
                        print("No valid price found. Closing calendar.")
                        page.mouse.click(0, 0)
                else:
                    print("Calendar failed to open.")

                # 2.3 Search
                print("Searching...")
                page.click(".TVSearchButton", force=True)

                # 2.4 Wait for Results
                try:
                    page.wait_for_selector(".TVHotelResultItem", timeout=20000)
                except:
                    if page.is_visible(".TVResultHelpFormHeader") and "не найдено" in page.inner_text(".TVResultHelpFormHeader"):
                        print("No results found.")
                        continue
                    print("Timeout waiting for results.")
                    continue

                # 2.5 Extract Data
                # Get the first (cheapest) card
                card = page.query_selector(".TVHotelResultItem")
                if card:
                    hotel_name = card.query_selector(".TVResultItemTitle").inner_text().strip()
                    print(f"Parsing Hotel: {hotel_name}")

                    # Expand "Rooms"
                    # Try clicking the "Rooms" button to reveal the table
                    try:
                        # Sometimes text is 'Номера', sometimes 'Туры'
                        btn = card.query_selector(".TVResultNavButton:has-text('Номера')") or \
                              card.query_selector(".TVResultNavButton:has-text('Туры')")
                        if btn:
                            btn.click(force=True)
                            page.wait_for_selector(".TVResultToursContent t-tbody t-tr", timeout=10000)
                    except:
                        pass

                    # Parse Table Row
                    # The table structure in Tourvisor usually has tds for specific columns
                    # We look for standard tr/td OR custom t-tr/t-td (observed in some versions)
                    row = page.query_selector(".TVResultToursContent t-tbody t-tr") or \
                          page.query_selector(".TVResultToursContent tbody tr")

                    item = {
                        "Страна": country,
                        "Отель": hotel_name,
                        "Цена": "N/A",
                        "Дата вылета": "N/A",
                        "Ночей": "N/A",
                        "Номер": "N/A",
                        "Питание": "N/A",
                        "Авиакомпания": "N/A",
                        "Дата прилета (расчетная)": "N/A"
                    }

                    if row:
                        # Try standard or custom cells
                        cells = row.query_selector_all("t-td") or row.query_selector_all("td")
                        texts = [c.inner_text().strip() for c in cells]

                        # Robust extraction based on common layout
                        if len(texts) >= 1: item["Номер"] = texts[0]
                        if len(texts) >= 2: item["Питание"] = texts[1]

                        # Date/Nights is often in one cell like "15.01 \n 7 ночей"
                        if len(texts) >= 3:
                            parts = texts[2].split('\n')
                            dep_date = parts[0] if len(parts) > 0 else texts[2]
                            nights = parts[1] if len(parts) > 1 else ""
                            item["Дата вылета"] = dep_date
                            item["Ночей"] = nights

                            # Try to calculate Arrival Date (approximate)
                            # Tourvisor format is usually dd.mm
                            try:
                                import datetime
                                current_year = datetime.datetime.now().year
                                # Parse dd.mm
                                d_day, d_month = map(int, dep_date.strip().split('.'))
                                d_nights = int(re.sub(r'\D', '', nights))

                                dep_dt = datetime.datetime(current_year, d_month, d_day)
                                # Handle year rollover
                                if dep_dt < datetime.datetime.now():
                                     dep_dt = dep_dt.replace(year=current_year + 1)

                                arr_dt = dep_dt + datetime.timedelta(days=d_nights)
                                item["Дата прилета (расчетная)"] = arr_dt.strftime("%d.%m")
                            except:
                                item["Дата прилета (расчетная)"] = "N/A"

                        # Price is usually the last one or near end
                        if len(texts) >= 1: item["Цена"] = texts[-1]

                        # Airline often in image title
                        img = row.query_selector("img")
                        if img: item["Авиакомпания"] = img.get_attribute("title") or "Unknown"

                    else:
                        # Fallback to card info
                        main_p = card.query_selector(".TVResultItemPriceValue")
                        if main_p: item["Цена"] = main_p.inner_text()

                    results.append(item)
                    print(f"Saved: {item}")

            except Exception as e:
                print(f"Error: {e}")
                # Reset page
                page.goto("https://algritravel.kz/", timeout=60000)
                try: page.wait_for_selector(".TVCountryFilter", timeout=10000)
                except: pass

        browser.close()

    if results:
        df = pd.DataFrame(results)
        df.to_csv("cheapest_tours.csv", index=False)
        print(f"Successfully saved {len(results)} tours.")
    else:
        print("No tours found.")

if __name__ == "__main__":
    scrape_algritravel()
