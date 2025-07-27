#!/usr/bin/env python3
"""
Debug script to examine the PAL product page pricing structure
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

def debug_pal_product_page():
    """Debug the PAL product page specifically"""
    
    print("🔍 Debug: PAL Product Page Analysis")
    print("=" * 50)
    
    driver = None
    try:
        driver = get_chrome_driver()
        driver.set_page_load_timeout(30)
        
        # Direct URL to PAL version
        url = "https://www.pricecharting.com/game/pal-psp/castlevania-the-dracula-x-chronicles"
        
        print(f"🌐 Navigating to: {url}")
        driver.get(url)
        time.sleep(3)
        
        print(f"📋 Final URL: {driver.current_url}")
        print(f"📄 Page Title: {driver.title}")
        
        # Look for the main pricing table
        print(f"\n💰 Analyzing pricing structure...")
        
        # Find all price elements
        price_elements = driver.find_elements(By.CSS_SELECTOR, "td.price, .js-price")
        
        print(f"Found {len(price_elements)} price elements:")
        for i, elem in enumerate(price_elements):
            price_text = elem.text.strip()
            parent_text = ""
            try:
                parent = elem.find_element(By.XPATH, "../..")
                parent_text = parent.text.strip()[:100]  # First 100 chars
            except:
                try:
                    parent = elem.find_element(By.XPATH, "..")
                    parent_text = parent.text.strip()[:100]
                except:
                    pass
            
            print(f"  {i}: '{price_text}' (context: {parent_text})")
        
        # Look for the specific price table structure
        print(f"\n📊 Looking for price table rows...")
        
        # Method 1: Find table rows with pricing data
        rows = driver.find_elements(By.CSS_SELECTOR, "tr")
        price_rows = []
        
        for i, row in enumerate(rows):
            row_text = row.text.strip()
            if '$' in row_text and any(keyword in row_text.lower() for keyword in ['loose', 'complete', 'new', 'cib']):
                price_rows.append((i, row_text))
                print(f"  Price Row {i}: {row_text}")
        
        # Method 2: Find the main pricing section
        print(f"\n🎯 Looking for main price guide...")
        
        # Look for the price guide table specifically
        try:
            # Common selectors for PriceCharting price tables
            price_tables = driver.find_elements(By.CSS_SELECTOR, "table.price-guide, .price-guide table, table")
            
            for j, table in enumerate(price_tables):
                table_text = table.text.strip()
                if '$' in table_text and 'price' in table_text.lower():
                    print(f"\n  Price Table {j}:")
                    print(f"  {table_text[:500]}...")  # First 500 chars
                    
                    # Extract individual rows
                    table_rows = table.find_elements(By.CSS_SELECTOR, "tr")
                    for k, tr in enumerate(table_rows[:10]):  # First 10 rows
                        cells = tr.find_elements(By.CSS_SELECTOR, "td, th")
                        if cells:
                            cell_texts = [cell.text.strip() for cell in cells]
                            if any('$' in text for text in cell_texts):
                                print(f"    Row {k}: {cell_texts}")
        
        except Exception as e:
            print(f"Error analyzing price tables: {e}")
        
        # Method 3: JavaScript extraction to see all dollar values
        print(f"\n🔧 JavaScript price extraction...")
        
        js_result = driver.execute_script("""
            var prices = [];
            var elements = document.querySelectorAll('*');
            
            for (var i = 0; i < elements.length; i++) {
                var text = elements[i].textContent;
                if (text && text.match(/\\$\\d+\\.\\d+/)) {
                    var matches = text.match(/\\$\\d+\\.\\d+/g);
                    if (matches) {
                        for (var j = 0; j < matches.length; j++) {
                            var context = text.substring(Math.max(0, text.indexOf(matches[j]) - 50), 
                                                      text.indexOf(matches[j]) + matches[j].length + 50);
                            prices.push({
                                price: matches[j],
                                context: context.trim(),
                                tag: elements[i].tagName
                            });
                        }
                    }
                }
            }
            
            return prices.slice(0, 20);  // Return first 20 matches
        """)
        
        print(f"Found {len(js_result)} price matches:")
        for result in js_result:
            print(f"  {result['price']} ({result['tag']}): {result['context']}")
        
        # Method 4: Check for specific expected values
        print(f"\n🔍 Checking for expected values...")
        
        expected_values = ["41.14", "63.94", "90.51", "290.84"]
        
        for value in expected_values:
            elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{value}')]")
            print(f"  ${value}: Found {len(elements)} matches")
            for elem in elements[:3]:  # Show first 3 matches
                context = elem.text.strip()
                parent_context = ""
                try:
                    parent = elem.find_element(By.XPATH, "..")
                    parent_context = parent.text.strip()[:200]
                except:
                    pass
                print(f"    Context: {context} | Parent: {parent_context}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.quit()
            
    print(f"\n✅ PAL product page analysis complete!")

if __name__ == "__main__":
    # Enable detailed logging
    logging.basicConfig(level=logging.INFO)
    debug_pal_product_page()
