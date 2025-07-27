#!/usr/bin/env python3
"""
Test script for PriceCharting scraper
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

from frontend.modules.scrapers import scrape_pricecharting_price

def test_pricecharting_scraper():
    """Test the PriceCharting scraper with a known game"""
    
    print("🎮 Testing PriceCharting Scraper")
    print("=" * 50)
    
    # Test with a popular game that should be found
    test_games = [
        ("Super Mario 64", "Nintendo 64"),
        ("The Legend of Zelda Ocarina of Time", "Nintendo 64"),
        ("Pokemon Red", "Game Boy"),
    ]
    
    for game_title, platform in test_games:
        print(f"\n🔍 Testing: {game_title} ({platform})")
        print("-" * 30)
        
        try:
            result = scrape_pricecharting_price(game_title, platform)
            
            if result:
                print("✅ Success! Found pricing data:")
                print(f"   Product Name: {result.get('product_name', 'N/A')}")
                print(f"   Console: {result.get('console_name', 'N/A')}")
                print(f"   Loose Price: ${result.get('loose_price', 'N/A')}")
                print(f"   CIB Price: ${result.get('cib_price', 'N/A')}")
                print(f"   New Price: ${result.get('new_price', 'N/A')}")
                print(f"   Source: {result.get('source', 'N/A')}")
            else:
                print("❌ No data found")
                
        except Exception as e:
            print(f"❌ Error occurred: {str(e)}")
    
    print(f"\n🏁 Test completed!")

if __name__ == "__main__":
    test_pricecharting_scraper()
