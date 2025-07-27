#!/usr/bin/env python3
"""
Enhanced debug script to trace PriceCharting URL handling and HTML parsing
"""
import sys
import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By

# Add the project root to sys.path so we can import modules
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import required functions
from frontend.modules.scrapers import get_chrome_driver

def debug_pricecharting_urls():
    """Debug the URL building and page navigation process"""
    
    print("🔍 Debug: PriceCharting URL and Page Analysis")
    print("=" * 60)
    
    driver = None
    try:
        driver = get_chrome_driver()
        driver.set_page_load_timeout(30)
        
        game_title = "Castlevania X Dracula Chronicles"
        platform = "PSP"
        region = "PAL"
        
        # Step 1: Build search query
        search_query = game_title
        if platform:
            search_query += f" {platform}"
        
        print(f"🔎 Search Query: '{search_query}'")
        
        # Step 2: Build search URL
        import urllib.parse
        encoded_search = urllib.parse.quote_plus(search_query)
        search_url = f"https://www.pricecharting.com/search-products?q={encoded_search}&type=prices"
        
        print(f"🌐 Search URL: {search_url}")
        
        # Step 3: Navigate to search page
        print("\n📡 Navigating to search page...")
        driver.get(search_url)
        time.sleep(3)
        
        print(f"📋 Current URL: {driver.current_url}")
        print(f"📄 Page Title: {driver.title}")
        
        # Step 4: Look for product links
        print("\n🔍 Looking for product links...")
        product_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/game/']")
        alt_links = driver.find_elements(By.CSS_SELECTOR, "td.title a")
        
        print(f"Found {len(product_links)} product links (primary selector)")
        print(f"Found {len(alt_links)} product links (alternative selector)")
        
        all_links = []
        for link in product_links[:5]:  # Show first 5
            href = link.get_attribute('href')
            text = link.text.strip()
            all_links.append((href, text))
            print(f"  📎 Primary: {href} -> '{text}'")
            
        for link in alt_links[:5]:  # Show first 5
            href = link.get_attribute('href')
            text = link.text.strip()
            if (href, text) not in all_links:
                all_links.append((href, text))
                print(f"  📎 Alt: {href} -> '{text}'")
        
        if not all_links:
            print("❌ No product links found!")
            
            # Debug: Let's see what's actually on the page
            print("\n🔍 Page source excerpt:")
            page_source = driver.page_source[:2000]
            print(page_source)
            return
        
        # Step 5: Pick the first product link and analyze it
        product_link, product_text = all_links[0]
        print(f"\n🎯 Selected product: {product_link} -> '{product_text}'")
        
        # Step 6: Apply region prefix
        original_link = product_link
        region_prefix = ""
        if region.upper() == "PAL":
            region_prefix = "pal-"
        elif region.upper() == "JAPAN":
            region_prefix = "jp-"
        
        if region_prefix and not region_prefix in product_link:
            if '/game/' in product_link:
                url_parts = product_link.split('/game/')
                if len(url_parts) > 1:
                    path_parts = url_parts[1].split('/')
                    if len(path_parts) > 0:
                        console_part = path_parts[0]
                        if not console_part.startswith(region_prefix):
                            path_parts[0] = region_prefix + console_part
                            product_link = url_parts[0] + '/game/' + '/'.join(path_parts)
        
        print(f"🌍 Region: {region}")
        print(f"🔗 Original link: {original_link}")
        print(f"🔗 Modified link: {product_link}")
        
        # Step 7: Navigate to product page
        print(f"\n📡 Navigating to product page...")
        driver.get(product_link)
        time.sleep(3)
        
        print(f"📋 Product URL: {driver.current_url}")
        print(f"📄 Product Title: {driver.title}")
        
        # Step 8: Analyze the pricing table structure
        print(f"\n📊 Analyzing pricing table...")
        
        # Look for table headers
        headers = driver.find_elements(By.CSS_SELECTOR, "th")
        header_texts = [h.text.strip() for h in headers]
        print(f"📋 Table headers found: {header_texts}")
        
        # Look for table rows
        rows = driver.find_elements(By.CSS_SELECTOR, "tr")
        print(f"📋 Table rows found: {len(rows)}")
        
        for i, row in enumerate(rows[:10]):  # Show first 10 rows
            cells = row.find_elements(By.CSS_SELECTOR, "td")
            cell_texts = [cell.text.strip() for cell in cells]
            if cell_texts:  # Only show non-empty rows
                print(f"  Row {i}: {cell_texts}")
        
        # Step 9: Look for specific price patterns
        print(f"\n💰 Looking for price patterns...")
        
        # Find all elements containing dollar signs
        price_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '$')]")
        print(f"Found {len(price_elements)} elements with '$' symbol")
        
        for i, elem in enumerate(price_elements[:10]):  # Show first 10
            text = elem.text.strip()
            tag = elem.tag_name
            print(f"  Price element {i} ({tag}): '{text}'")
        
        # Step 10: Test JavaScript extraction
        print(f"\n🔧 Testing JavaScript price extraction...")
        
        js_result = driver.execute_script("""
            var priceData = {};
            var allText = document.body.innerText;
            
            // Look for price table structure
            var tables = document.querySelectorAll('table');
            console.log('Found', tables.length, 'tables');
            
            for (var t = 0; t < tables.length; t++) {
                var table = tables[t];
                var rows = table.querySelectorAll('tr');
                
                for (var r = 0; r < rows.length; r++) {
                    var row = rows[r];
                    var cells = row.querySelectorAll('td, th');
                    var rowText = row.innerText.toLowerCase();
                    
                    if (rowText.includes('loose') || rowText.includes('complete') || rowText.includes('new')) {
                        var cellTexts = [];
                        for (var c = 0; c < cells.length; c++) {
                            cellTexts.push(cells[c].innerText.trim());
                        }
                        
                        console.log('Potential price row:', cellTexts);
                        
                        // Look for prices in this row
                        for (var c = 0; c < cells.length; c++) {
                            var cellText = cells[c].innerText;
                            var priceMatch = cellText.match(/\\$([\\d,]+\\.?\\d*)/);
                            if (priceMatch) {
                                if (rowText.includes('loose')) priceData.loose = priceMatch[1];
                                if (rowText.includes('complete') || rowText.includes('cib')) priceData.cib = priceMatch[1];
                                if (rowText.includes('new')) priceData.new = priceMatch[1];
                            }
                        }
                    }
                }
            }
            
            return priceData;
        """)
        
        print(f"JavaScript extraction result: {js_result}")
        
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.quit()
            
    print(f"\n✅ Debug analysis complete!")

if __name__ == "__main__":
    # Enable more detailed logging
    logging.basicConfig(level=logging.INFO)
    debug_pricecharting_urls()
