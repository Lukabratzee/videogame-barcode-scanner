import pytest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.scrapers import scrape_ebay_prices


@pytest.mark.ebay
def test_ebay_scraper_must_work():
    """
    Test eBay scraper with a known game title - must return a valid price.
    """
    query = "Ace Combat 04 Shattered Skies PlayStation 2"
    price = scrape_ebay_prices(query)
    print(f"eBay price for '{query}': {price}")
    
    # Strict test - must return a valid price
    assert isinstance(price, (int, float)) and price > 0
