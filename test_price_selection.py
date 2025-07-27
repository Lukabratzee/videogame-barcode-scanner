#!/usr/bin/env python3
"""
Test the price selection logic for PriceCharting
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

from frontend.modules.scrapers import get_best_pricecharting_price

def test_price_selection():
    """Test the price selection logic"""
    
    print("🎯 Testing PriceCharting Price Selection Logic")
    print("=" * 50)
    
    # Test case 1: All prices available
    test_data_1 = {
        'loose_price': 27.19,
        'cib_price': 292.28,
        'new_price': 6873.0,
        'source': 'PriceCharting'
    }
    
    selected_price_1 = get_best_pricecharting_price(test_data_1)
    print(f"\n📊 Test 1 - All prices available:")
    print(f"   Loose: £{test_data_1['loose_price']}")
    print(f"   CIB: £{test_data_1['cib_price']}")
    print(f"   New: £{test_data_1['new_price']}")
    print(f"   ✅ Selected: £{selected_price_1} (Should prioritize Loose)")
    
    # Test case 2: Missing loose price
    test_data_2 = {
        'loose_price': None,
        'cib_price': 292.28,
        'new_price': 6873.0,
        'source': 'PriceCharting'
    }
    
    selected_price_2 = get_best_pricecharting_price(test_data_2)
    print(f"\n📊 Test 2 - No loose price:")
    print(f"   Loose: {test_data_2['loose_price']}")
    print(f"   CIB: £{test_data_2['cib_price']}")
    print(f"   New: £{test_data_2['new_price']}")
    print(f"   ✅ Selected: £{selected_price_2} (Should fallback to CIB)")
    
    # Test case 3: Only new price available
    test_data_3 = {
        'loose_price': None,
        'cib_price': None,
        'new_price': 6873.0,
        'source': 'PriceCharting'
    }
    
    selected_price_3 = get_best_pricecharting_price(test_data_3)
    print(f"\n📊 Test 3 - Only new price:")
    print(f"   Loose: {test_data_3['loose_price']}")
    print(f"   CIB: {test_data_3['cib_price']}")
    print(f"   New: £{test_data_3['new_price']}")
    print(f"   ✅ Selected: £{selected_price_3} (Should fallback to New)")
    
    # Test case 4: No prices available
    test_data_4 = {
        'loose_price': None,
        'cib_price': None,
        'new_price': None,
        'source': 'PriceCharting'
    }
    
    selected_price_4 = get_best_pricecharting_price(test_data_4)
    print(f"\n📊 Test 4 - No prices:")
    print(f"   Loose: {test_data_4['loose_price']}")
    print(f"   CIB: {test_data_4['cib_price']}")
    print(f"   New: {test_data_4['new_price']}")
    print(f"   ✅ Selected: {selected_price_4} (Should be None)")
    
    print(f"\n🏁 Price selection tests completed!")
    
    # Verify expected results
    assert selected_price_1 == 27.19, f"Expected 27.19, got {selected_price_1}"
    assert selected_price_2 == 292.28, f"Expected 292.28, got {selected_price_2}"
    assert selected_price_3 == 6873.0, f"Expected 6873.0, got {selected_price_3}"
    assert selected_price_4 is None, f"Expected None, got {selected_price_4}"
    
    print("✅ All tests passed!")

if __name__ == "__main__":
    test_price_selection()
