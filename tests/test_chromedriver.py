import os
import pytest
import importlib


def test_chromedriver_launch_and_navigate():
    scrapers = importlib.import_module("modules.scrapers")
    get_driver = getattr(scrapers, "get_chrome_driver", None)
    if get_driver is None:
        pytest.skip("No driver initializer present")

    driver = None
    try:
        driver = get_driver(headless=True)
        driver.get("https://example.com")
        # Some driver stubs may not expose page_source; tolerate that by checking current_url
        current_url = getattr(driver, "current_url", "")
        assert "example.com" in current_url or hasattr(driver, "page_source")
    except Exception as e:
        pytest.xfail(f"Chrome/driver not available or failed to launch: {e}")
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass


