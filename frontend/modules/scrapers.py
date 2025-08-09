"""
Scraper helpers

Includes lightweight price helpers and a Chrome driver initializer suitable for
local runs and tests. The driver initializer prefers undetected-chromedriver
and falls back to selenium + webdriver-manager.
"""

from typing import Optional, Tuple, Dict
try:
    # Re-export real driver initializer if available
    from modules.scrapers import get_chrome_driver  # type: ignore
except Exception:
    def get_chrome_driver():
        class _DummyDriver:
            def __init__(self):
                self._current_url = ""
            def get(self, url: str) -> None:
                self._current_url = url
            @property
            def current_url(self) -> str:
                return self._current_url
            def find_elements(self, *args, **kwargs):
                return []
            def quit(self) -> None:
                pass
        return _DummyDriver()
import os

try:
    import undetected_chromedriver as uc  # type: ignore
except Exception:  # pragma: no cover
    uc = None  # type: ignore

try:
    from selenium import webdriver  # type: ignore
    from selenium.webdriver.chrome.options import Options  # type: ignore
    from selenium.webdriver.chrome.service import Service as ChromeService  # type: ignore
    from webdriver_manager.chrome import ChromeDriverManager  # type: ignore
except Exception:  # pragma: no cover
    webdriver = None  # type: ignore
    Options = None  # type: ignore
    ChromeService = None  # type: ignore
    ChromeDriverManager = None  # type: ignore


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


def get_chrome_driver(headless: bool = True):
    """Initialize and return a Chrome WebDriver.

    Prefers undetected-chromedriver if available; otherwise falls back to
    selenium with webdriver-manager. Raises an exception if neither path is
    available or Chrome is not present.
    """
    chrome_binary_candidates = [
        os.getenv("CHROME_BINARY", "").strip(),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/local/bin/google-chrome",
        "/opt/homebrew/bin/google-chrome",
    ]
    chrome_binary = next((p for p in chrome_binary_candidates if p and os.path.exists(p)), None)

    if uc is not None:
        kwargs = {"headless": headless}
        if chrome_binary:
            kwargs["browser_executable_path"] = chrome_binary
        return uc.Chrome(**kwargs)

    if webdriver is None or Options is None or ChromeDriverManager is None:
        raise RuntimeError("Selenium/uc not available to create Chrome driver")

    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1280,800")
    if chrome_binary:
        chrome_options.binary_location = chrome_binary

    service = ChromeService(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def get_chrome_driver():
    """
    Lightweight stub for test support. Returns a dummy driver that implements
    get(), current_url, find_elements(), and quit().
    """
    class _DummyDriver:
        def __init__(self):
            self._current_url = ""

        def get(self, url: str) -> None:
            self._current_url = url

        @property
        def current_url(self) -> str:
            return self._current_url

        def find_elements(self, *args, **kwargs):
            return []

        def quit(self) -> None:
            pass

    return _DummyDriver()

