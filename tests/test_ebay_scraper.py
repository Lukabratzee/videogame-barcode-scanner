import pytest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.scrapers import scrape_ebay_prices


@pytest.mark.ebay
def test_ebay_scraper_smoke():
    """
    Smoke test for eBay scraper. eBay may throttle/block automated headless sessions
    intermittently; if we receive None, mark as xfail instead of failing the suite.
    """
    query = "Ace Combat 04 Shattered Skies PlayStation 2"
    price = scrape_ebay_prices(query)
    print(f"eBay price for '{query}': {price}")
    if price is None:
        pytest.xfail("eBay occasionally blocks headless scraping; allowing xfail in CI.")
    assert isinstance(price, (int, float)) and price > 0
