"""
Lightweight scraper stubs and helpers

This file provides minimal implementations for the scraping functions used by
the application, along with helper functions for selecting PriceCharting
values. Full selenium-based implementations can be restored later if needed.
"""

from typing import Optional, Tuple, Dict


def get_best_pricecharting_price(pricing_data: Optional[Dict]) -> Optional[float]:
    """Return a representative price from PriceCharting (loose -> CIB -> new)."""
    if not pricing_data or not isinstance(pricing_data, dict):
        return None
    if pricing_data.get("loose_price") is not None:
        return pricing_data["loose_price"]
    if pricing_data.get("cib_price") is not None:
        return pricing_data["cib_price"]
    if pricing_data.get("new_price") is not None:
        return pricing_data["new_price"]
    return None


def get_pricecharting_price_by_condition(pricing_data: Optional[Dict], prefer_boxed: bool = True) -> Optional[float]:
    """Select a price depending on condition preference."""
    if not pricing_data or not isinstance(pricing_data, dict):
        return None
    if prefer_boxed:
        return (
            pricing_data.get("cib_price")
            or pricing_data.get("loose_price")
            or pricing_data.get("new_price")
        )
    return (
        pricing_data.get("loose_price")
        or pricing_data.get("cib_price")
        or pricing_data.get("new_price")
    )


def scrape_pricecharting_price(game_title: str, platform: Optional[str] = None, region: Optional[str] = None) -> Optional[Dict]:
    """
    Placeholder PriceCharting scraper – return None to indicate unavailable.
    The application will handle None gracefully.
    """
    return None


def scrape_ebay_prices(query: str) -> Optional[float]:
    """Placeholder eBay scraper – return None to indicate unavailable."""
    return None


def scrape_cex_price(query: str) -> Optional[float]:
    """Placeholder CeX scraper – return None to indicate unavailable."""
    return None


def scrape_amazon_price(query: str) -> Optional[float]:
    """Placeholder Amazon scraper – return None to indicate unavailable."""
    return None


def scrape_barcode_lookup(barcode: str) -> Tuple[Optional[str], Optional[float]]:
    """Placeholder barcode lookup – return (None, None)."""
    return None, None


