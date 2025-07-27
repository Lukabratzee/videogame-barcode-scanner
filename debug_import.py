#!/usr/bin/env python3
"""
Debug import path to see which scrapers.py file is actually being used
"""
import sys
import os

# Add the project root to sys.path exactly like frontend.py does
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

print("🔍 Import Path Debug")
print("=" * 50)
print(f"Python sys.path:")
for i, path in enumerate(sys.path):
    print(f"  {i}: {path}")

print(f"\nProject root: {PROJECT_ROOT}")

try:
    # Import the same way frontend.py does
    from modules.scrapers import scrape_pricecharting_price
    
    # Show which file was actually imported
    import modules.scrapers
    scrapers_file = modules.scrapers.__file__
    print(f"\n✅ Successfully imported scrapers from: {scrapers_file}")
    
    # Check if it has our version marker
    import inspect
    source = inspect.getsource(scrape_pricecharting_price)
    if "LATEST VERSION - 2025-07-27" in source:
        print("✅ Using LATEST VERSION with fixes")
    else:
        print("❌ Using OLD VERSION - this is the problem!")
    
    # Show the first few lines of the function
    lines = source.split('\n')[:10]
    print(f"\nFunction definition preview:")
    for line in lines:
        print(f"  {line}")
        
except ImportError as e:
    print(f"❌ Import failed: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print(f"\n✅ Debug complete!")
