#!/usr/bin/env python3
"""
Test the actual PriceCharting scraper function
"""
import sys
import os
import logging

# Add the project root to sys.path so we can import modules
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import required functions
from frontend.modules.scrapers import scrape_pricecharting_price

def test_pricecharting_scraper():
    """Test the actual scraper function"""
    
    print("🔍 Testing PriceCharting Scraper Function")
    print("=" * 50)
    
    # Enable detailed logging
    logging.basicConfig(level=logging.INFO)
    
    # Test with PAL region and prefer_boxed=True (CiB)
    print(f"\n💰 Testing: Castlevania Dracula X Chronicles (PAL, CiB)")
    result = scrape_pricecharting_price("Castlevania Dracula X Chronicles", region="PAL")
    
    print(f"📊 Result: {result}")
    
    # Test specific conditions
    print(f"\n📋 Testing all pricing data extraction...")
    from frontend.modules.scrapers import get_chrome_driver
    import time
    
    driver = None
    try:
        driver = get_chrome_driver()
        
        # Navigate directly to PAL page
        url = "https://www.pricecharting.com/game/pal-psp/castlevania-the-dracula-x-chronicles"
        print(f"🌐 Direct navigation to: {url}")
        
        driver.get(url)
        time.sleep(3)
        
        print(f"📋 Final URL: {driver.current_url}")
        
        # Import the scrape function we want to test
        
        # Manually create pricing data by calling the extract function
        from selenium.webdriver.common.by import By
        import re
        
        def convert_usd_to_gbp(usd_price):
            return round(usd_price * 0.79, 2)
        
        pricing_data = {
            'loose_price': None,
            'loose_price_usd': None,
            'cib_price': None,
            'cib_price_usd': None,
            'new_price': None,
            'new_price_usd': None,
        }
        
        # Test with current scraper logic
        print(f"\n🔧 Manual price extraction test...")
        
        try:
            # Look for the price section directly
            price_rows = driver.find_elements(By.CSS_SELECTOR, "tr")
            
            for row in price_rows:
                try:
                    cells = row.find_elements(By.CSS_SELECTOR, "td, th")
                    if len(cells) >= 2:
                        cell_texts = [cell.text.strip().lower() for cell in cells]
                        row_text = ' '.join(cell_texts)
                        
                        if 'loose' in row_text:
                            for cell in cells:
                                price_match = re.search(r'\$([0-9,]+\.?[0-9]*)', cell.text)
                                if price_match:
                                    usd_price = float(price_match.group(1).replace(',', ''))
                                    print(f"  Loose: ${usd_price} -> £{convert_usd_to_gbp(usd_price)}")
                                    break
                        
                        if 'complete' in row_text:
                            for cell in cells:
                                price_match = re.search(r'\$([0-9,]+\.?[0-9]*)', cell.text)
                                if price_match:
                                    usd_price = float(price_match.group(1).replace(',', ''))
                                    print(f"  Complete: ${usd_price} -> £{convert_usd_to_gbp(usd_price)}")
                                    break
                        
                        if 'new' in row_text and 'graded' not in row_text:
                            for cell in cells:
                                price_match = re.search(r'\$([0-9,]+\.?[0-9]*)', cell.text)
                                if price_match:
                                    usd_price = float(price_match.group(1).replace(',', ''))
                                    print(f"  New (non-graded): ${usd_price} -> £{convert_usd_to_gbp(usd_price)}")
                                    break
                        
                        if 'graded new' in row_text:
                            for cell in cells:
                                price_match = re.search(r'\$([0-9,]+\.?[0-9]*)', cell.text)
                                if price_match:
                                    usd_price = float(price_match.group(1).replace(',', ''))
                                    print(f"  Graded New (should be excluded): ${usd_price} -> £{convert_usd_to_gbp(usd_price)}")
                                    break
                
                except Exception as e:
                    pass
        
        except Exception as e:
            print(f"❌ Manual extraction error: {e}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.quit()
    
    print(f"\n✅ Scraper test complete!")

if __name__ == "__main__":
    test_pricecharting_scraper()
