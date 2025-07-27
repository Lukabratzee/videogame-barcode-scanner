#!/usr/bin/env python3
"""
Advanced debug script to manually verify PriceCharting URLs and data
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

def test_manual_urls():
    """Test the specific URLs that should give us the correct prices"""
    
    print("🔍 Manual URL Testing for Castlevania Dracula X Chronicles")
    print("=" * 70)
    
    # URLs to test based on our debug findings
    urls_to_test = [
        ("US Search Results", "https://www.pricecharting.com/search-products?q=Castlevania+X+Dracula+Chronicles+PSP&type=prices"),
        ("US Direct Product", "https://www.pricecharting.com/game/psp/castlevania-dracula-x-chronicles"),
        ("PAL Direct Product", "https://www.pricecharting.com/game/pal-psp/castlevania-the-dracula-x-chronicles"),
        ("PAL Alternative", "https://www.pricecharting.com/game/pal-psp/castlevania-dracula-x-chronicles"),
    ]
    
    driver = None
    try:
        driver = get_chrome_driver()
        driver.set_page_load_timeout(30)
        
        for url_name, url in urls_to_test:
            print(f"\n🌐 Testing: {url_name}")
            print(f"🔗 URL: {url}")
            print("-" * 50)
            
            try:
                driver.get(url)
                time.sleep(3)
                
                print(f"📋 Final URL: {driver.current_url}")
                print(f"📄 Page Title: {driver.title}")
                
                # Look for price table
                print("\n💰 Looking for pricing data...")
                
                # Method 1: Look for table structure
                try:
                    rows = driver.find_elements(By.CSS_SELECTOR, "tr")
                    print(f"Found {len(rows)} table rows")
                    
                    for i, row in enumerate(rows[:8]):  # Show first 8 rows
                        cells = row.find_elements(By.CSS_SELECTOR, "td, th")
                        if cells:
                            cell_texts = [cell.text.strip() for cell in cells]
                            if any('$' in text for text in cell_texts):  # Only show rows with prices
                                print(f"  Row {i}: {cell_texts}")
                                
                                # Special check for Castlevania entries
                                row_text = ' '.join(cell_texts).lower()
                                if 'castlevania' in row_text and 'dracula' in row_text:
                                    print(f"    🎯 MATCH: This row contains Castlevania!")
                                    
                                    # Extract specific prices from this row
                                    for j, cell_text in enumerate(cell_texts):
                                        if '$' in cell_text:
                                            print(f"      Column {j}: {cell_text}")
                                    
                except Exception as e:
                    print(f"Table parsing error: {e}")
                
                # Method 2: Look for specific price elements
                print("\n🔍 Searching for specific price patterns...")
                price_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '$')]")
                
                castlevania_prices = []
                for elem in price_elements:
                    parent_text = ""
                    try:
                        # Get context from parent elements
                        parent = elem.find_element(By.XPATH, "..")
                        parent_text = parent.text.lower()
                    except:
                        pass
                    
                    if 'castlevania' in parent_text or 'dracula' in parent_text:
                        price_text = elem.text.strip()
                        castlevania_prices.append((price_text, parent_text[:100]))
                
                if castlevania_prices:
                    print("🎯 Found Castlevania-related prices:")
                    for price, context in castlevania_prices[:10]:  # Show first 10
                        print(f"  💲 {price} (context: {context})")
                else:
                    print("❌ No Castlevania-specific prices found")
                
                # Method 3: Check page source for the exact values we expect
                print("\n🔍 Checking for expected price values...")
                page_source = driver.page_source.lower()
                
                expected_prices = ["63.94", "41.14", "90.51"]  # The prices we manually verified
                found_expected = []
                
                for price in expected_prices:
                    if price in page_source:
                        found_expected.append(price)
                        print(f"  ✅ Found expected price: ${price}")
                        
                        # Try to find context around this price
                        import re
                        pattern = f".{{0,100}}{re.escape(price)}.{{0,100}}"
                        matches = re.findall(pattern, page_source)
                        if matches:
                            for match in matches[:2]:  # Show first 2 contexts
                                clean_match = ' '.join(match.split())  # Clean whitespace
                                print(f"      Context: ...{clean_match}...")
                
                if not found_expected:
                    print("❌ None of the expected prices found on this page")
                else:
                    print(f"✅ Found {len(found_expected)}/{len(expected_prices)} expected prices")
                
            except Exception as e:
                print(f"❌ Error accessing {url_name}: {e}")
                
    except Exception as e:
        print(f"❌ Driver initialization error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.quit()
            
    print(f"\n✅ Manual URL testing complete!")

if __name__ == "__main__":
    # Enable detailed logging
    logging.basicConfig(level=logging.INFO)
    test_manual_urls()
