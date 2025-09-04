import asyncio
import os
import time
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

def clear_terminal():
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

async def fetch_crypto_data(page):
    """Fetches and prints the cryptocurrency data."""
    try:
        await page.reload(timeout=60000)
        await page.wait_for_selector('div.tableContainer', timeout=30000)
        html_content = await page.content()

        soup = BeautifulSoup(html_content, 'html.parser')

        table = soup.find('table', class_='yf-1m4mc7b')
        if not table:
            print("Could not find the data table.")
            return

        rows = table.find('tbody').find_all('tr', attrs={'data-testid': 'data-table-v2-row'})

        if not rows:
            print("Could not find any data rows in the table.")
            return

        clear_terminal()
        print("Yahoo Finance Top 10 Cryptocurrencies (Live)")
        print(f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 140)
        print("{:<15} | {:<25} | {:<15} | {:<15} | {:<15} | {:<15} | {:<15}".format(
            "Symbol", "Name", "Price (Intraday)", "Change", "% Change", "Market Cap", "Volume in Currency (24Hr)"
        ))
        print("-" * 140)

        for row in rows[:10]:
            cols = row.find_all('td')

            if len(cols) >= 7:
                symbol = cols[0].text.strip()
                name = cols[1].text.strip()
                price = cols[3].text.strip()
                change = cols[4].text.strip()
                percent_change = cols[5].text.strip()
                market_cap = cols[6].text.strip()
                volume = cols[8].text.strip()

                print("{:<15} | {:<25} | {:<15} | {:<15} | {:<15} | {:<15} | {:<15}".format(
                    symbol, name, price, change, percent_change, market_cap, volume
                ))

    except Exception as e:
        print(f"An error occurred during data fetch: {e}")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto('https://finance.yahoo.com/markets/crypto/', timeout=60000)

            while True:
                await fetch_crypto_data(page)
                await asyncio.sleep(10)

        except KeyboardInterrupt:
            print("\nScraper stopped by user.")
        except Exception as e:
            print(f"A critical error occurred: {e}")
            error_html = await page.content()
            with open('error_page.html', 'w', encoding='utf-8') as f:
                f.write(error_html)
            print("Error page HTML saved to error_page.html")

        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
