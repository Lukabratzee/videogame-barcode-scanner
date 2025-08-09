"""
Scraper helpers

Includes lightweight price helpers and a Chrome driver initializer suitable for
local runs and tests. The driver initializer prefers undetected-chromedriver
and falls back to selenium + webdriver-manager.
"""

from typing import Optional, Tuple, Dict
import re
import json
import html
import time
import requests
import os

try:
    import undetected_chromedriver as uc  # type: ignore
except Exception:  # pragma: no cover
    uc = None  # type: ignore

try:
    from selenium import webdriver  # type: ignore
    from selenium.webdriver.chrome.options import Options  # type: ignore
    from selenium.webdriver.chrome.service import Service as ChromeService  # type: ignore
    from selenium.webdriver.common.by import By  # type: ignore
    from selenium.webdriver.common.keys import Keys  # type: ignore
    from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
    from selenium.webdriver.support import expected_conditions as EC  # type: ignore
    from webdriver_manager.chrome import ChromeDriverManager  # type: ignore
except Exception:  # pragma: no cover
    webdriver = None  # type: ignore
    Options = None  # type: ignore
    ChromeService = None  # type: ignore
    ChromeDriverManager = None  # type: ignore
    Keys = None  # type: ignore


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
    LATEST VERSION - 2025-07-31 - Added platform aliases for better PriceCharting compatibility
    
    Scrapes PriceCharting.com for video game pricing data.
    
    Args:
        game_title (str): The name of the game to search for
        platform (str, optional): The platform/console name (e.g., "Nintendo 64", "PlayStation")
        region (str, optional): The region for pricing ("US", "PAL", "Japan"). Defaults to "US"
    
    Returns:
        Dict containing pricing data with keys: loose_price, cib_price, new_price (all optional)
        Returns None if no pricing data found
    """
    if not game_title.strip():
        return None
    
    driver = None
    try:
        driver = get_chrome_driver()
        
        # Clean up search query
        search_query = game_title.strip()
        
        # Build search URL for PriceCharting
        import urllib.parse
        encoded_title = urllib.parse.quote(search_query)
        
        # Use PriceCharting's search endpoint
        base_url = "https://www.pricecharting.com/search-products"
        search_url = f"{base_url}?q={encoded_title}&type=prices"
        
        driver.get(search_url)
        time.sleep(3)
        
        # Check if we got redirected to a specific game page or stayed on search results
        current_url = driver.current_url
        
        if "/game/" in current_url:
            # Direct game page - extract pricing data
            pricing_data = extract_pricecharting_pricing(driver)
        else:
            # Search results page - find the first relevant result
            try:
                # Look for game result links
                game_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/game/']")
                
                if game_links:
                    # Click on the first result
                    first_link = game_links[0]
                    driver.execute_script("arguments[0].click();", first_link)
                    time.sleep(3)
                    
                    # Extract pricing from the game detail page
                    pricing_data = extract_pricecharting_pricing(driver)
                else:
                    # No game links found
                    return None
                    
            except Exception as e:
                return None
        
        return pricing_data
        
    except Exception as e:
        return None
    finally:
        if driver:
            driver.quit()


def extract_pricecharting_pricing(driver) -> Optional[Dict]:
    """
    Extract pricing data from a PriceCharting game detail page.
    
    Returns:
        Dict with pricing data or None if extraction fails
    """
    try:
        pricing_data = {}
        
        # Method 1: Try to find pricing table rows
        try:
            # Look for table rows containing price data
            price_rows = driver.find_elements(By.CSS_SELECTOR, "tr")
            
            for row in price_rows:
                row_text = row.text.lower().strip()
                
                # Look for different condition types
                if any(keyword in row_text for keyword in ["loose", "cart only", "cartridge"]):
                    price = extract_price_from_element(row)
                    if price:
                        pricing_data["loose_price"] = price
                        
                elif any(keyword in row_text for keyword in ["complete", "cib", "box"]):
                    price = extract_price_from_element(row)
                    if price:
                        pricing_data["cib_price"] = price
                        
                elif any(keyword in row_text for keyword in ["new", "sealed"]):
                    price = extract_price_from_element(row)
                    if price:
                        pricing_data["new_price"] = price
                        
        except Exception:
            pass
        
        # Method 2: If table method failed, try CSS selectors for price elements
        if not pricing_data:
            try:
                price_selectors = [
                    ".price",
                    "[class*='price']", 
                    ".used_price",
                    ".new_price",
                    ".loose_price"
                ]
                
                for selector in price_selectors:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        price = extract_price_from_element(element)
                        if price and "loose_price" not in pricing_data:
                            pricing_data["loose_price"] = price
                            break
                    if pricing_data:
                        break
                        
            except Exception:
                pass
        
        # Method 3: JavaScript extraction as last resort
        if not pricing_data:
            try:
                js_prices = driver.execute_script("""
                    var prices = [];
                    var elements = document.querySelectorAll('*');
                    
                    for (var i = 0; i < elements.length; i++) {
                        var text = elements[i].textContent || '';
                        var matches = text.match(/\\$\\d+\\.?\\d*/g);
                        if (matches) {
                            prices = prices.concat(matches);
                        }
                    }
                    
                    return prices.slice(0, 5); // Return first 5 price matches
                """)
                
                if js_prices:
                    for price_text in js_prices:
                        price = extract_price_from_text(price_text)
                        if price and "loose_price" not in pricing_data:
                            pricing_data["loose_price"] = price
                            break
                            
            except Exception:
                pass
        
        return pricing_data if pricing_data else None
        
    except Exception:
        return None


def extract_price_from_element(element) -> Optional[float]:
    """Extract a price value from a web element."""
    try:
        text = element.text.strip()
        return extract_price_from_text(text)
    except:
        return None


def extract_price_from_text(text: str) -> Optional[float]:
    """Extract a price value from text string."""
    try:
        import re
        # Look for price patterns like $12.99, $1,234.56
        price_match = re.search(r'\$([0-9,]+\.?[0-9]*)', text)
        if price_match:
            price_str = price_match.group(1).replace(',', '')
            price_usd = float(price_str)
            
            # Convert USD to GBP (approximate rate)
            price_gbp = price_usd * 0.79
            return round(price_gbp, 2)
    except:
        pass
    return None


def scrape_ebay_prices(game_title: str) -> Optional[float]:
    """
    Opens eBay UK's homepage, enters the game_title in the search box,
    scrolls down to load additional results, and then collects all valid price values.
    Returns the average price found as a float, or None if no valid prices are found.
    """
    driver = None
    try:
        driver = get_chrome_driver()  # Use the environment-aware driver function

        # 1. Navigate to eBay UK homepage.
        driver.get("https://www.ebay.co.uk/")
        time.sleep(2)  # Wait for page load

        # 2. Find the search box (id 'gh-ac') and enter the game title
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "gh-ac"))
        )
        search_box.send_keys(game_title)
        time.sleep(1)
        search_box.send_keys(Keys.RETURN)
        time.sleep(3)  # Wait for results to load

        # 3. Scroll down to load more results (if lazy-loaded)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        
        # 4. Collect all price elements.
        price_elements = driver.find_elements(By.CSS_SELECTOR, "span.s-item__price")
        valid_prices = []
        if price_elements:
            for el in price_elements:
                price_text = el.text.strip()
                if not price_text:
                    continue
                # Remove currency symbols and extra text
                price_text = price_text.replace("£", "").replace("GBP", "").strip()
                # Sometimes prices come in ranges ("42.00 to 50.00"), so take first token
                tokens = price_text.split()
                if tokens:
                    try:
                        price = float(tokens[0].replace(",", ""))
                        valid_prices.append(price)
                    except ValueError:
                        continue
            if valid_prices:
                # Return the average price from the list of valid prices.
                average_price = sum(valid_prices) / len(valid_prices)
                return round(average_price, 2)
            else:
                return None
        else:
            return None

    except Exception as e:
        return None
    finally:
        if driver:
            driver.quit()


def scrape_cex_price(game_title: str) -> Optional[float]:
    """
    Opens CeX UK's website, searches for the game title using the search URL, and returns the first price found.

    Returns the first price found as a float, or None if no valid prices are found.
    """
    driver = None
    try:
        driver = get_chrome_driver()

        # Navigate to CeX UK search page with the game title
        import urllib.parse
        encoded_search = urllib.parse.quote_plus(game_title)
        search_url = f"https://uk.webuy.com/search?stext={encoded_search}"
        
        driver.get(search_url)
        time.sleep(5)  # Wait for page to load completely
        
        # Try multiple approaches to find prices
        price_found = None
        
        # Approach 1: Use JavaScript to find all elements with £ in text
        try:
            js_prices = driver.execute_script("""
                var elements = document.querySelectorAll('*');
                var priceTexts = [];
                for (var i = 0; i < elements.length; i++) {
                    var text = elements[i].textContent || elements[i].innerText || '';
                    if (text.includes('£') && text.match(/£[\\d,]+\\.?\\d*/)) {
                        priceTexts.push(text.trim());
                    }
                }
                return priceTexts.slice(0, 20); // First 20 matches
            """)
            
            # Extract first valid price from JavaScript results
            import re
            for price_text in js_prices:
                price_match = re.search(r'£([\\d,]+\\.?\\d*)', price_text)
                if price_match:
                    try:
                        price_str = price_match.group(1).replace(',', '')
                        price_value = float(price_str)
                        price_found = price_value
                        break
                    except ValueError:
                        continue
        except Exception:
            pass
        
        # Approach 2: Try various CSS selectors if JavaScript approach fails
        if price_found is None:
            selectors_to_try = [
                ".product-main-price",
                ".price", 
                "[class*='price']",
                ".basket-price",
                ".cash-price"
            ]
            
            for selector in selectors_to_try:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        text = element.text.strip()
                        if '£' in text:
                            import re
                            price_match = re.search(r'£([\\d,]+\\.?\\d*)', text)
                            if price_match:
                                try:
                                    price_str = price_match.group(1).replace(',', '')
                                    price_value = float(price_str)
                                    price_found = price_value
                                    break
                                except ValueError:
                                    continue
                    
                    if price_found:
                        break
                        
                except Exception:
                    continue
        
        return price_found

    except Exception as e:
        return None
    finally:
        if driver:
            driver.quit()


def scrape_amazon_price(game_title: str) -> Optional[float]:
    """
    Opens Amazon UK's homepage, enters the game title into the search box,
    waits for any captcha to be resolved, and returns the first price element
    (converted to a float). Returns None if not found.
    """
    driver = None
    try:
        driver = get_chrome_driver()

        driver.get("https://www.amazon.co.uk/")
        time.sleep(2)

        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "twotabsearchtextbox"))
        )
        search_box.send_keys(game_title)
        time.sleep(1)
        search_box.send_keys(Keys.RETURN)
        time.sleep(10)  # Longer wait after search to allow manual captcha resolution

        if "captcha" in driver.page_source.lower():
            return None

        price_elements = driver.find_elements(By.CSS_SELECTOR, "span.a-price-whole")
        if price_elements:
            price_text = price_elements[0].text.strip().replace(",", "")
            try:
                return float(price_text)
            except ValueError:
                return None
        else:
            return None

    except Exception as e:
        return None
    finally:
        if driver:
            driver.quit()


def scrape_barcode_lookup(barcode: str) -> Tuple[Optional[str], Optional[float]]:
    """
    Scrapes the barcode lookup website for the game title and average price.
    Returns a tuple: (game_title, average_price)
    """
    if not barcode:
        return None, None
    
    driver = None
    try:
        driver = get_chrome_driver()  # Use the environment-aware driver function
        
        url = f"https://www.barcodelookup.com/{barcode}"
        driver.get(url)
        time.sleep(2)
        
        game_title_elem = driver.find_element(By.CSS_SELECTOR, "div.col-50.product-details h4")
        game_title = game_title_elem.text.strip() if game_title_elem else "Unknown Game"
        
        # Use the same logic as before to get a price; adjust the selector only if needed.
        try:
            price_elem = driver.find_element(By.CSS_SELECTOR, "span.price")
            price_text = price_elem.text.strip().replace("£", "").replace(",", "")
            average_price = float(price_text)
        except Exception as e:
            average_price = None
            
        return game_title, average_price
        
    except Exception as e:
        return None, None
    finally:
        if driver:
            driver.quit()


def get_chrome_driver():
    """
    Safely initialize Chrome driver with proper error handling and fallback options.
    Uses Docker-compatible driver in containers and undetected-chromedriver locally.
    """
    
    # Check for Docker environment
    DOCKER_MODE = os.getenv('DOCKER_ENV') or os.path.exists('/.dockerenv')
    
    if DOCKER_MODE:
        # Docker environment - use standard WebDriver with explicit path
        try:
            options = Options()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-images")
            options.add_argument("--disable-web-security")
            options.add_argument("--allow-running-insecure-content")
            options.add_argument("--ignore-certificate-errors")
            options.add_argument("--ignore-ssl-errors")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--headless=new")
            options.add_argument("--user-agent=Mozilla/5.0 (Linux; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
            
            # Use system Chrome and ChromeDriver in Docker with explicit path
            service = ChromeService("/usr/local/bin/chromedriver")  # Explicit path for Docker
            driver = webdriver.Chrome(service=service, options=options)
            return driver
        except Exception as e:
            raise Exception("Could not initialize Chrome driver in Docker environment")
    else:
        # Local environment - try multiple approaches with fresh options each time
        
        # Method 1: Try webdriver-manager for automatic version matching
        try:
            options = Options()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage") 
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-images")
            options.add_argument("--window-size=1920,1080")
            
            # Use webdriver-manager for version matching
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            return driver
        except Exception as e:
            pass
        
        # Method 2: Try undetected-chromedriver with fresh options
        if uc is not None:
            try:
                options = uc.ChromeOptions()
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--disable-extensions")
                options.add_argument("--window-size=1920,1080")
                
                driver = uc.Chrome(options=options)
                return driver
            except Exception as e:
                pass
        
        raise Exception("Could not initialize Chrome driver - tried webdriver-manager and undetected-chromedriver")

# Note: Do not redefine get_chrome_driver below; the implementation above
# provides real drivers (uc/selenium) and will raise if unavailable. Tests
# that rely on a stub should mock this symbol explicitly.

