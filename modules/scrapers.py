# scrapers.py
import time
import logging
import re 
import requests
import os

# Conditional imports for Docker vs local environment
try:
    # Check for Docker environment first  
    if os.getenv('DOCKER_ENV') or os.path.exists('/.dockerenv'):
        print("🐳 Docker environment detected in scrapers.py - using standard selenium")
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.chrome.service import Service as ChromeService
        # Set flag for Docker mode
        DOCKER_MODE = True
    else:
        # Local environment imports
        print("💻 Local environment detected in scrapers.py - using undetected-chromedriver")
        import undetected_chromedriver as uc
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.service import Service as ChromeService
        # Set flag for local mode
        DOCKER_MODE = False
except ImportError as e:
    print(f"⚠️ Import warning in scrapers.py: {e}")
    # Fallback to basic selenium 
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.chrome.service import Service as ChromeService
        DOCKER_MODE = True
    except ImportError:
        print("❌ No selenium available in scrapers.py - scraper functions will be disabled")
        DOCKER_MODE = True

# Use environment variable or default paths for Docker/local development
import os
driver_path = os.getenv("CHROMEDRIVER_BIN", "/opt/homebrew/bin/chromedriver")  

def get_chrome_driver():
    """
    Safely initialize Chrome driver with proper error handling and fallback options.
    Uses Docker-compatible driver in containers and undetected-chromedriver locally.
    """
    options = get_chrome_options()
    
    if DOCKER_MODE:
        # Docker environment - use standard WebDriver with explicit path
        try:
            # Use system Chrome and ChromeDriver in Docker with explicit path
            service = ChromeService("/usr/bin/chromedriver")  # Explicit path for Docker
            driver = webdriver.Chrome(service=service, options=options)
            logging.info("Successfully initialized standard Chrome driver for Docker")
            return driver
        except Exception as e:
            logging.error(f"Failed to initialize Chrome driver in Docker: {e}")
            raise Exception("Could not initialize Chrome driver in Docker environment")
    else:
        # Local environment - use undetected_chromedriver
        try:
            # Try with specified service path first
            service = ChromeService(driver_path)
            driver = uc.Chrome(service=service, options=options)
            logging.info(f"Successfully initialized undetected Chrome driver with path: {driver_path}")
            return driver
        except Exception as e:
            logging.warning(f"Failed to initialize Chrome driver with path {driver_path}: {e}")
            
            try:
                # Fallback: let undetected_chromedriver manage the driver automatically
                driver = uc.Chrome(options=options)
                logging.info("Successfully initialized Chrome driver with automatic path detection")
                return driver
            except Exception as e2:
                logging.error(f"Failed to initialize Chrome driver with automatic detection: {e2}")
                raise Exception("Could not initialize Chrome driver with any method")

def get_chrome_options():
    """Configure Chrome options for both Docker and local environments"""
    if DOCKER_MODE:
        options = Options()  # Standard Chrome options for Docker
    else:
        options = uc.ChromeOptions()  # Undetected Chrome options for local
    
    # Essential arguments for headless operation and Docker
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
    options.add_argument("--ignore-certificate-errors-spki-list")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--remote-debugging-port=0")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-ipc-flooding-protection")
    
    # Set window size for consistent layout
    options.add_argument("--window-size=1920,1080")
    
    # User agent to avoid detection
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    
    # Set Chrome binary path if provided via environment
    chrome_bin = os.getenv("CHROME_BIN")
    if chrome_bin:
        options.binary_location = chrome_bin
    
    # Force headless mode in Docker environment
    # Check if we're in a Docker container (DISPLAY env var typically set)
    in_docker = os.getenv("DISPLAY") or os.path.exists("/.dockerenv")
    if in_docker or DOCKER_MODE:
        options.add_argument("--headless=new")  # Use new headless mode
        logging.info("Running in Docker environment - enabling headless mode")
    
    return options  

def scrape_barcode_lookup(barcode):
    """
    Scrapes the barcode lookup website for the game title and average price.
    Returns a tuple: (game_title, average_price)
    """
    driver = get_chrome_driver()  # Use the environment-aware driver function
    
    try:
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
            logging.warning(f"Unable to parse price on barcode lookup: {e}")
            average_price = None
    except Exception as e:
        logging.error(f"Error in scrape_barcode_lookup: {e}")
        game_title, average_price = None, None
    finally:
        driver.quit()
    return game_title, average_price

def scrape_amazon_price(game_title):
    """
    Opens Amazon UK's homepage, enters the game title into the search box,
    waits for any captcha to be resolved, and returns the first price element
    (converted to a float). Returns None if not found.
    """
    driver = get_chrome_driver()  # Use the environment-aware driver function

    try:
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
            logging.error("Amazon CAPTCHA still present; aborting scrape.")
            return None

        price_elements = driver.find_elements(By.CSS_SELECTOR, "span.a-price-whole")
        if price_elements:
            price_text = price_elements[0].text.strip().replace(",", "")
            try:
                return float(price_text)
            except ValueError:
                logging.warning(f"Could not convert Amazon price text '{price_text}' to float.")
                return None
        else:
            logging.warning("No price elements found on Amazon search page.")
            return None

    except Exception as e:
        logging.error(f"Error scraping Amazon: {e}")
        return None
    finally:
        driver.quit()

def scrape_ebay_prices(game_title):
    """
    Opens eBay UK's homepage, enters the game_title in the search box,
    scrolls down to load additional results, and then collects all valid price values.
    Returns the lowest price found as a float, or None if no valid prices are found.
    """
    driver = get_chrome_driver()  # Use the environment-aware driver function

    try:
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
                        logging.debug(f"Found price: {price}")
                    except ValueError:
                        continue
            if valid_prices:
                # Return the average or lowest price from the list of valid prices.
                lowest_price = min(valid_prices)
                logging.debug(f"Returning lowest price: {lowest_price}")
                return sum(valid_prices) / len(valid_prices)
                # return lowest_price
            else:
                logging.warning("No valid numeric prices found among the price elements.")
                return None
        else:
            logging.warning("No price elements found on the eBay search page.")
            return None

    except Exception as e:
        logging.error(f"Error scraping eBay: {e}")
        return None
    finally:
        driver.quit()

def scrape_cex_price(game_title):
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
                    if (text.includes('£') && text.match(/£[\d,]+\.?\d*/)) {
                        priceTexts.push(text.trim());
                    }
                }
                return priceTexts.slice(0, 20); // First 20 matches
            """)
            
            # Extract first valid price from JavaScript results
            import re
            for price_text in js_prices:
                price_match = re.search(r'£([\d,]+\.?\d*)', price_text)
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
                            price_match = re.search(r'£([\d,]+\.?\d*)', text)
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
        logging.error(f"Error scraping CeX: {e}")
        return None
    finally:
        if driver:
            driver.quit()