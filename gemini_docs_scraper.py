import asyncio
import csv
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import urllib.parse

BASE_URL = "https://geminicli.com/docs/"
OUTPUT_FILE = "gemini_docs.csv"

async def get_links(page):
    """Extracts all documentation links from the sidebar or main content."""
    # This selector targets the sidebar links based on the text structure I observed
    # or generic anchor tags within the page.
    # Looking at the text dump, there are lists of links.
    # I'll grab all links on the page and filter them.
    links = await page.evaluate('''() => {
        const anchors = Array.from(document.querySelectorAll('a'));
        return anchors.map(a => a.href);
    }''')

    unique_links = set()
    for link in links:
        # Normalize the URL
        if not link:
            continue

        # We only want links within the docs section
        if link.startswith(BASE_URL):
            # Remove anchors (fragments) to avoid duplicates like #overview
            parsed = urllib.parse.urlparse(link)
            path = parsed.path
            if path.endswith('/') and len(path) > 1:
                path = path.rstrip('/')
            clean_link = parsed.scheme + "://" + parsed.netloc + path
            unique_links.add(clean_link)

    return sorted(list(unique_links))

async def scrape_page(context, url):
    """Visits a page and extracts title and content."""
    page = await context.new_page()
    try:
        print(f"Scraping: {url}")
        await page.goto(url)
        # Wait for some content to load.
        # I'll wait for 'h1' as a generic indicator.
        await page.wait_for_selector('h1', timeout=10000)

        content_html = await page.content()
        soup = BeautifulSoup(content_html, 'html.parser')

        # Extract title
        title = soup.find('h1').get_text(strip=True) if soup.find('h1') else "No Title"

        # Extract main content.
        # I'll try to find a main container. Common ones are <main>, <article>, or div with specific classes.
        # Based on typical documentation sites (and the text dump showing "Skip to content"),
        # there is likely a main area.
        main_content = soup.find('main')
        if not main_content:
            main_content = soup.find('article')
        if not main_content:
            # Fallback: body, but remove nav/headers if possible.
            # For now, let's just grab text from body but this might be noisy.
            # Let's hope for <main> or similar.
            main_content = soup.body

        # Clean up the text
        text_content = main_content.get_text(separator='\n', strip=True)

        return {
            'url': page.url, # Return final URL after redirects
            'title': title,
            'content': text_content
        }

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None
    finally:
        await page.close()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()

        # Start at the base URL to get the list of pages
        page = await context.new_page()
        await page.goto(BASE_URL)
        await page.wait_for_load_state("networkidle")

        print("Gathering links...")
        links = await get_links(page)
        print(f"Found {len(links)} unique links.")
        await page.close()

        results = []
        # Visit each link
        # Limit concurrency to avoid overloading or getting blocked
        semaphore = asyncio.Semaphore(5)

        async def bound_scrape(url):
            async with semaphore:
                return await scrape_page(context, url)

        tasks = [bound_scrape(link) for link in links]
        pages_data = await asyncio.gather(*tasks)

        # Filter out None results
        valid_data = [data for data in pages_data if data]

        # Deduplicate based on final URL
        unique_results = {}
        for data in valid_data:
            # Normalize final URL for deduplication (strip trailing slash)
            final_url = data['url']
            parsed = urllib.parse.urlparse(final_url)
            path = parsed.path
            if path.endswith('/') and len(path) > 1:
                path = path.rstrip('/')
            clean_final_url = parsed.scheme + "://" + parsed.netloc + path

            if clean_final_url not in unique_results:
                unique_results[clean_final_url] = data

        results = list(unique_results.values())

        # Save to CSV
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['title', 'url', 'content'])
            writer.writeheader()
            for row in results:
                writer.writerow(row)

        print(f"Saved {len(results)} pages to {OUTPUT_FILE}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
