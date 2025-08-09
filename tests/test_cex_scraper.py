import os
import sys
import pytest


# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from modules.scrapers import scrape_cex_price  # noqa: E402


@pytest.mark.cex
def test_cex_price_must_exist():
    """
    Smoke test: CeX price should be retrievable for a known title.

    Uses a PS2 title that reliably shows a price in list view with
    <p class="product-main-price">£X.XX</p>.
    """
    query = "Ace Combat - Distant Thunder PlayStation 2"
    price = scrape_cex_price(query)
    print(f"CeX price for '{query}': {price}")
    assert isinstance(price, (int, float)) and price > 0


