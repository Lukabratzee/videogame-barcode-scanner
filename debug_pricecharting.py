#!/usr/bin/env python3
"""
Debug script to test PriceCharting scraping for Castlevania X Chronicles
"""
import sys
import os

# Add the project root to sys.path so we can import modules
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import the scraping function
from frontend.modules.scrapers import scrape_pricecharting_price

def debug_castlevania_scraping():
    """Test the exact search that's causing issues"""
    
    print("🐛 Debug: PriceCharting scraping for Castlevania X Chronicles")
    print("=" * 60)
    
    # Test the exact search terms
    game_title = "Castlevania X Dracula Chronicles"
    platform = "PSP"
    region = "PAL"  # This should be the default
    
    print(f"Game Title: {game_title}")
    print(f"Platform: {platform}")
    print(f"Region: {region}")
    print()
    
    # Call the scraper
    print("Calling scrape_pricecharting_price()...")
    result = scrape_pricecharting_price(game_title, platform, region)
    
    if result:
        print("✅ Results found:")
        print(f"  Product Name: {result.get('product_name', 'N/A')}")
        print(f"  Console Name: {result.get('console_name', 'N/A')}")
        print(f"  Region: {result.get('region', 'N/A')}")
        print()
        print("💰 Pricing Data:")
        
        if result.get('loose_price'):
            usd_loose = result.get('loose_price_usd', 'N/A')
            print(f"  Loose Price: £{result['loose_price']:.2f} (${usd_loose})")
        else:
            print("  Loose Price: Not available")
            
        if result.get('cib_price'):
            usd_cib = result.get('cib_price_usd', 'N/A')
            print(f"  CiB Price: £{result['cib_price']:.2f} (${usd_cib})")
        else:
            print("  CiB Price: Not available")
            
        if result.get('new_price'):
            usd_new = result.get('new_price_usd', 'N/A')
            print(f"  New Price: £{result['new_price']:.2f} (${usd_new})")
        else:
            print("  New Price: Not available")
            
        print()
        print("🔍 Analysis:")
        if result.get('loose_price') == result.get('cib_price') == result.get('new_price'):
            print("  ⚠️  WARNING: All prices are identical - this suggests the scraper might be")
            print("      extracting the same value multiple times or finding only one price")
        
        # Check if the price matches the suspicious £16.72
        if any(price and abs(price - 16.72) < 0.01 for price in [result.get('loose_price'), result.get('cib_price'), result.get('new_price')]):
            print("  🚨 FOUND THE ISSUE: This matches the suspicious £16.72 price!")
            print("      Expected CiB price should be around £63.94 based on manual check")
            
    else:
        print("❌ No results found - scraper returned None")
        
    print()
    print("🔧 Troubleshooting suggestions:")
    print("1. Check if the search is finding the correct game variant")
    print("2. Verify the region URL prefix is being applied correctly")
    print("3. Ensure we're extracting from the Mid Price column, not Low Price")
    print("4. Check if the PSP platform is being searched correctly")

if __name__ == "__main__":
    debug_castlevania_scraping()
