#!/usr/bin/env python3
"""
Quick test of PriceCharting scraper after fixes
"""
import sys
import os
import logging

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import required functions
from frontend.modules.scrapers import scrape_pricecharting_price, get_pricecharting_price_by_condition

def test_current_scraper():
    """Test the current scraper state"""
    
    print("🔍 Testing Current PriceCharting Scraper")
    print("=" * 50)
    
    # Enable logging to see what's happening
    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
    
    # Test exact same parameters as frontend would use
    game_title = "Castlevania Dracula X Chronicles"
    platform = "PSP"  # This might be passed from frontend
    region = "PAL"
    prefer_boxed = True
    
    print(f"🎮 Game: {game_title}")
    print(f"🎯 Platform: {platform}")
    print(f"🌍 Region: {region}")
    print(f"📦 Prefer Boxed: {prefer_boxed}")
    print()
    
    # Call the scraper
    try:
        pricecharting_data = scrape_pricecharting_price(game_title, platform, region)
        
        if pricecharting_data:
            print("✅ Successfully scraped PriceCharting data:")
            print(f"   Source: {pricecharting_data.get('source', 'N/A')}")
            print(f"   Product: {pricecharting_data.get('product_name', 'N/A')}")
            print(f"   Region: {pricecharting_data.get('region', 'N/A')}")
            print()
            
            # Show all available prices
            if pricecharting_data.get('loose_price'):
                print(f"   💰 Loose Price: £{pricecharting_data['loose_price']:.2f} (${pricecharting_data.get('loose_price_usd', 'N/A')})")
            if pricecharting_data.get('cib_price'):
                print(f"   📦 CIB Price: £{pricecharting_data['cib_price']:.2f} (${pricecharting_data.get('cib_price_usd', 'N/A')})")
            if pricecharting_data.get('new_price'):
                print(f"   ✨ New Price: £{pricecharting_data['new_price']:.2f} (${pricecharting_data.get('new_price_usd', 'N/A')})")
            print()
            
            # Test condition-based selection
            selected_price = get_pricecharting_price_by_condition(pricecharting_data, prefer_boxed)
            condition_text = "Boxed (CiB)" if prefer_boxed else "Loose"
            
            print(f"🎯 Selected Condition: {condition_text}")
            print(f"💷 Selected Price: £{selected_price:.2f}")
            
            # Verify this matches what frontend should show
            expected_cib = pricecharting_data.get('cib_price')
            if prefer_boxed and expected_cib and selected_price == expected_cib:
                print("✅ Price selection logic working correctly")
            else:
                print("❌ Price selection logic issue detected")
                print(f"   Expected CIB: £{expected_cib}")
                print(f"   Got: £{selected_price}")
        
        else:
            print("❌ No data returned from scraper")
            
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n✅ Test complete!")

if __name__ == "__main__":
    test_current_scraper()
