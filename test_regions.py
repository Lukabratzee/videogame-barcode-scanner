#!/usr/bin/env python3
"""
Test the region functionality for PriceCharting
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

from frontend.modules.scrapers import scrape_pricecharting_price

def test_regions():
    """Test different regions for PriceCharting"""
    
    print("🌍 Testing PriceCharting Regional Pricing")
    print("=" * 50)
    
    # Test game
    game_title = "Super Mario 64"
    platform = "Nintendo 64"
    
    regions = ["US", "PAL", "Japan"]
    
    for region in regions:
        print(f"\n🎯 Testing {region} region...")
        try:
            result = scrape_pricecharting_price(game_title, platform, region)
            if result:
                print(f"✅ {region} - Found pricing data:")
                print(f"   Region: {result.get('region', 'Unknown')}")
                print(f"   Product: {result.get('product_name', 'Unknown')}")
                print(f"   Console: {result.get('console_name', 'Unknown')}")
                print(f"   Loose: £{result.get('loose_price', 'N/A')}")
                print(f"   CIB: £{result.get('cib_price', 'N/A')}")
                print(f"   New: £{result.get('new_price', 'N/A')}")
            else:
                print(f"❌ {region} - No data found")
                
        except Exception as e:
            print(f"❌ {region} - Error: {e}")
    
    print(f"\n🏁 Regional testing completed!")

if __name__ == "__main__":
    test_regions()
