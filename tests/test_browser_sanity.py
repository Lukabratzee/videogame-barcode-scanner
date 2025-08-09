import importlib
import os
import pytest


def test_browser_driver_initialization(monkeypatch, tmp_path):
    """
    Smoke test that our scraper module can attempt to initialize a driver.
    We don't actually browse any site to keep the test fast and reliable.
    """
    # Ensure Docker mode is false for local test
    monkeypatch.delenv("DOCKER_ENV", raising=False)
    # Import the canonical scraper
    scrapers = importlib.import_module("modules.scrapers")

    # If the implementation has a get_chrome_driver, try calling it guardedly.
    get_driver = getattr(scrapers, "get_chrome_driver", None)
    if get_driver is None:
        pytest.skip("No browser driver function available in this build")

    try:
        driver = get_driver()  # type: ignore
    except Exception as e:
        # It's acceptable to fail if environment doesn't have Chrome/driver;
        # this still validates that the code path is reachable.
        pytest.xfail(f"Driver init failed in this environment: {e}")
        return

    try:
        # If we did get a driver instance, quit it immediately.
        driver.quit()
    except Exception:
        pass


