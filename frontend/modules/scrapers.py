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

def get_best_pricecharting_price(pricing_data):
    """
    Get the best representative price from PriceCharting data.
    
    This mimics the "Mid Price" shown in PriceCharting's interface.
    Prioritizes: loose -> CIB -> new
    """
    if not pricing_data:
        return None
        
    # Try loose first (most common/accessible)
    if pricing_data.get('loose_price') is not None:
        return pricing_data['loose_price']
    
    # Fallback to CIB if no loose price
    if pricing_data.get('cib_price') is not None:
        return pricing_data['cib_price']
    
    # Final fallback to new price
    if pricing_data.get('new_price') is not None:
        return pricing_data['new_price']
    
    return None

def get_pricecharting_price_by_condition(pricing_data, prefer_boxed=True):
    """
    Get PriceCharting price based on boxed preference.
    
    Args:
        pricing_data (dict): The pricing data from PriceCharting
        prefer_boxed (bool): If True, prefer CiB price; if False, prefer loose price
    
    Returns:
        float or None: The selected price based on condition preference
    """
    if not pricing_data:
        return None
    
    if prefer_boxed:
        # Boxed preference: CiB -> loose -> new
        if pricing_data.get('cib_price') is not None:
            return pricing_data['cib_price']
        if pricing_data.get('loose_price') is not None:
            return pricing_data['loose_price']
        if pricing_data.get('new_price') is not None:
            return pricing_data['new_price']
    else:
        # Loose preference: loose -> CiB -> new
        if pricing_data.get('loose_price') is not None:
            return pricing_data['loose_price']
        if pricing_data.get('cib_price') is not None:
            return pricing_data['cib_price']
        if pricing_data.get('new_price') is not None:
            return pricing_data['new_price']
    
    return None

def convert_usd_to_gbp(usd_amount):
    """
    Convert USD to GBP using a reasonable exchange rate.
    For a more accurate conversion, you could use a live API, but for
    video game pricing, a static rate is usually sufficient.
    
    Current approximate rate: 1 USD = 0.79 GBP (July 2025)
    """
    if usd_amount is None:
        return None
    
    try:
        # Using approximate exchange rate - you can update this periodically
        # or integrate with a live currency API if needed
        exchange_rate = 0.79  # 1 USD = 0.79 GBP
        gbp_amount = float(usd_amount) * exchange_rate
        return round(gbp_amount, 2)  # Round to 2 decimal places
    except (ValueError, TypeError):
        return None
    """
    Convert USD to GBP using a reasonable exchange rate.
    For a more accurate conversion, you could use a live API, but for
    video game pricing, a static rate is usually sufficient.
    
    Current approximate rate: 1 USD = 0.79 GBP (July 2025)
    """
    if usd_amount is None:
        return None
    
    try:
        # Using approximate exchange rate - you can update this periodically
        # or integrate with a live currency API if needed
        exchange_rate = 0.79  # 1 USD = 0.79 GBP
        gbp_amount = float(usd_amount) * exchange_rate
        return round(gbp_amount, 2)  # Round to 2 decimal places
    except (ValueError, TypeError):
        return None  

def get_chrome_driver():
    """
    Safely initialize Chrome driver with proper error handling and fallback options.
    Uses Docker-compatible driver in containers and undetected-chromedriver locally.
    """
    
    if DOCKER_MODE:
        # Docker environment - use standard WebDriver with explicit path
        try:
            # Import selenium webdriver explicitly for Docker
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options as DockerOptions
            
            # Create options for Docker
            options = DockerOptions()
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
            logging.info("Successfully initialized standard Chrome driver for Docker")
            return driver
        except Exception as e:
            logging.error(f"Failed to initialize Chrome driver in Docker: {e}")
            raise Exception("Could not initialize Chrome driver in Docker environment")
    else:
        # Local environment - try multiple approaches with fresh options each time
        
        # Method 1: Try webdriver-manager for automatic version matching
        try:
            from selenium.webdriver.chrome.options import Options as StandardOptions
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium import webdriver
            
            options = StandardOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage") 
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            logging.info("Successfully initialized Chrome driver with webdriver-manager")
            return driver
        except Exception as e:
            logging.warning(f"Failed with webdriver-manager: {e}")
        
        # Method 2: Try undetected-chromedriver with automatic download
        try:
            options = uc.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu") 
            options.add_argument("--disable-extensions")
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1920,1080")
            
            # Let undetected_chromedriver handle version matching automatically
            driver = uc.Chrome(options=options, version_main=None)
            logging.info("Successfully initialized undetected Chrome driver with auto-version")
            return driver
        except Exception as e:
            logging.warning(f"Failed with undetected_chromedriver auto-version: {e}")
        
        # Method 3: Try system ChromeDriver with standard selenium
        try:
            from selenium.webdriver.chrome.options import Options as StandardOptions
            
            options = StandardOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1920,1080")
            
            service = ChromeService(driver_path)
            driver = webdriver.Chrome(service=service, options=options)
            logging.info(f"Successfully initialized standard Chrome driver with path: {driver_path}")
            return driver
        except Exception as e:
            logging.warning(f"Failed with system ChromeDriver: {e}")
        
        # All methods failed
        logging.error("All Chrome driver initialization methods failed")
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
    
    Enhanced with better resource management and anti-detection measures.
    """
    driver = None
    try:
        # Get driver with enhanced options for Amazon
        driver = get_amazon_chrome_driver()
        
        # Set page load timeout to prevent hanging
        driver.set_page_load_timeout(30)
        
        # Navigate to Amazon UK with retry logic
        max_retries = 2
        for attempt in range(max_retries):
            try:
                logging.info(f"Attempting to load Amazon UK (attempt {attempt + 1}/{max_retries})")
                driver.get("https://www.amazon.co.uk/")
                break
            except Exception as e:
                logging.warning(f"Failed to load Amazon on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    raise e
                time.sleep(2)
        
        # Wait for page to load and check for CAPTCHA immediately
        time.sleep(3)
        
        # Check for CAPTCHA or robot detection early
        page_source = driver.page_source.lower()
        if any(keyword in page_source for keyword in ["captcha", "robot", "verify", "security"]):
            logging.error("Amazon detected automation or CAPTCHA present; aborting scrape.")
            return None
        
        # Find search box with shorter timeout
        try:
            search_box = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.ID, "twotabsearchtextbox"))
            )
        except Exception:
            logging.error("Could not find Amazon search box within timeout")
            return None
        
        # Clear and enter search term
        search_box.clear()
        search_box.send_keys(game_title + " video game")  # Add context to improve results
        time.sleep(1)
        
        # Submit search
        search_box.send_keys(Keys.RETURN)
        
        # Wait for results with timeout
        try:
            WebDriverWait(driver, 15).until(
                lambda d: "s-result-item" in d.page_source or "captcha" in d.page_source.lower()
            )
        except Exception:
            logging.error("Amazon search results did not load within timeout")
            return None
        
        # Check again for CAPTCHA after search
        if "captcha" in driver.page_source.lower():
            logging.error("Amazon CAPTCHA appeared after search; aborting scrape.")
            return None
        
        # Try multiple price selectors (Amazon changes them frequently)
        price_selectors = [
            "span.a-price-whole",
            ".a-price-whole", 
            "span[class*='price-whole']",
            ".a-price .a-offscreen",
            "span.a-price.a-text-price.a-size-medium.a-color-base",
            ".a-price-range .a-price.a-text-normal .a-price-whole"
        ]
        
        price_found = None
        for selector in price_selectors:
            try:
                price_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if price_elements:
                    for element in price_elements[:3]:  # Check first 3 elements
                        try:
                            price_text = element.text.strip().replace(",", "")
                            if price_text and price_text.replace(".", "").isdigit():
                                price_found = float(price_text)
                                logging.info(f"Found Amazon price: £{price_found} using selector: {selector}")
                                break
                        except (ValueError, AttributeError):
                            continue
                    if price_found:
                        break
            except Exception:
                continue
        
        return price_found

    except Exception as e:
        logging.error(f"Error scraping Amazon: {e}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass  # Ignore errors during cleanup

def get_amazon_chrome_driver():
    """
    Get Chrome driver with enhanced options specifically for Amazon scraping.
    Includes additional anti-detection measures.
    """
    if DOCKER_MODE:
        options = Options()
        service = ChromeService("/usr/local/bin/chromedriver")
    else:
        options = uc.ChromeOptions()
        driver_path = os.getenv("CHROMEDRIVER_BIN", "/opt/homebrew/bin/chromedriver")
        service = ChromeService(driver_path)
    
    # Enhanced options for Amazon
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")  # Reduce resource usage
    options.add_argument("--disable-javascript")  # Reduce resource usage
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
    
    # Memory and performance optimizations
    options.add_argument("--memory-pressure-off")
    options.add_argument("--max_old_space_size=4096")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-client-side-phishing-detection")
    
    # Set smaller window size to reduce memory usage
    options.add_argument("--window-size=1280,720")
    
    # Enhanced user agent for Amazon
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")
    
    # Set Chrome binary path if provided
    chrome_bin = os.getenv("CHROME_BIN")
    if chrome_bin:
        options.binary_location = chrome_bin
    
    # Force headless mode in Docker environment
    in_docker = os.getenv("DISPLAY") or os.path.exists("/.dockerenv")
    if in_docker or DOCKER_MODE:
        options.add_argument("--headless=new")
        logging.info("Amazon scraper running in Docker environment - enabling headless mode")
    
    try:
        if DOCKER_MODE:
            # Import selenium webdriver explicitly for Docker
            from selenium import webdriver
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = uc.Chrome(service=service, options=options)
        
        logging.info("Successfully initialized enhanced Chrome driver for Amazon")
        return driver
    except Exception as e:
        logging.error(f"Failed to initialize enhanced Chrome driver for Amazon: {e}")
        raise Exception("Could not initialize enhanced Chrome driver for Amazon")

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

def scrape_pricecharting_price(game_title, platform=None, region=None):
    """
    LATEST VERSION - 2025-07-31 - Added platform aliases for better PriceCharting compatibility
    
    Scrapes PriceCharting.com for video game pricing data.
    
    Args:
        game_title (str): The name of the game to search for
        platform (str, optional): The platform/console name (e.g., "Nintendo 64", "PlayStation")
        region (str, optional): The region for pricing ("US", "PAL", "Japan"). Defaults to "US"
    
    Returns:
        dict: Dictionary containing pricing data with keys:
            - loose_price: Price for game only (float or None)
            - cib_price: Complete in box price (float or None) 
            - new_price: New/sealed price (float or None)
            - source: Always "PriceCharting"
            - product_name: Game title from PriceCharting
            - console_name: Console name from PriceCharting
            - region: The region used for pricing
        Returns None if no data found or error occurred.
    """
    driver = None
    try:
        driver = get_chrome_driver()
        driver.set_page_load_timeout(30)
        
        # Default to PAL region if not specified
        if region is None:
            region = "PAL"
        
        # Platform aliases mapping - converts database platform names to PriceCharting-expected names
        # This ensures better search accuracy by using the exact platform names PriceCharting recognizes
        PLATFORM_ALIASES = {
            # Sony Platforms
            "PlayStation Portable": "PSP",
            "PlayStation": "PlayStation",
            "PlayStation 2": "PlayStation 2", 
            "PlayStation 3": "PlayStation 3",
            "PlayStation 4": "PlayStation 4",
            "PlayStation 5": "PlayStation 5",
            "PlayStation Vita": "Vita",
            "PSP": "PSP",
            "PS1": "PlayStation",
            "PS2": "PlayStation 2",
            "PS3": "PlayStation 3", 
            "PS4": "PlayStation 4",
            "PS5": "PlayStation 5",
            "PSVita": "Vita",
            "Vita": "Vita",
            
            # Nintendo Platforms
            "Nintendo 64": "Nintendo 64",
            "Nintendo GameCube": "GameCube",
            "Nintendo Wii": "Wii",
            "Nintendo Wii U": "Wii U", 
            "Nintendo Switch": "Switch",
            "Nintendo DS": "DS",
            "Nintendo 3DS": "3DS",
            "Game Boy": "Game Boy",
            "Game Boy Color": "Game Boy Color",
            "Game Boy Advance": "Game Boy Advance",
            "Nintendo Entertainment System": "NES",
            "Super Nintendo Entertainment System": "Super Nintendo",
            "N64": "Nintendo 64",
            "GameCube": "GameCube",
            "Wii": "Wii",
            "Wii U": "Wii U",
            "Switch": "Switch",
            "DS": "DS",
            "3DS": "3DS",
            "GBA": "Game Boy Advance",
            "GBC": "Game Boy Color",
            "GB": "Game Boy",
            "NES": "NES",
            "SNES": "Super Nintendo",
            
            # Microsoft Platforms
            "Xbox": "Xbox",
            "Xbox 360": "Xbox 360",
            "Xbox One": "Xbox One",
            "Xbox Series X": "Xbox Series X",
            "Xbox Series S": "Xbox Series X",  # PriceCharting groups Series S with Series X
            
            # Sega Platforms
            "Sega Genesis": "Sega Genesis",
            "Sega Dreamcast": "Dreamcast",
            "Sega Saturn": "Sega Saturn",
            "Sega Master System": "Sega Master System",
            "Sega Game Gear": "Game Gear",
            "Genesis": "Sega Genesis",
            "Dreamcast": "Dreamcast",
            "Saturn": "Sega Saturn",
            
            # Atari Platforms
            "Atari 2600": "Atari 2600",
            "Atari 7800": "Atari 7800",
            
            # PC Platforms  
            "PC": "PC",
            "Windows": "PC",
            "Mac": "Mac",
            "Linux": "PC",
            
            # Other Platforms
            "Neo Geo": "Neo Geo",
            "TurboGrafx-16": "TurboGrafx-16",
            "Arcade": "Arcade"
        }
        
        # Apply platform alias if platform is provided
        if platform and platform in PLATFORM_ALIASES:
            original_platform = platform
            platform = PLATFORM_ALIASES[platform]
            logging.info(f"Platform alias applied: '{original_platform}' -> '{platform}'")
        
        # Search for the game on PriceCharting with regional specificity
        search_query = game_title
        if platform:
            search_query += f" {platform}"
        
        # Function to perform search with a given query
        def search_with_query(query):
            # Use PriceCharting's search URL structure with proper region parameter
            # PriceCharting tracks multiple regional variants (PAL, NTSC, Japan) with different pricing
            import urllib.parse
            encoded_search = urllib.parse.quote_plus(query)
            
            # Build URL - note we don't use region parameter as it filters out results
            base_url = "https://www.pricecharting.com/search-products"
            params = {
                "type": "prices",
                "q": encoded_search,
                "sort": "popularity", 
                "broad-category": "all",
                "console-uid": "",
                "exclude-variants": "false",
                "show-images": "true"
            }
            
            # Construct the full URL
            search_url = base_url + "?" + urllib.parse.urlencode(params)
            
            logging.info(f"Searching PriceCharting ({region}) for: {query}")
            driver.get(search_url)
            time.sleep(3)
            
            # Check if we found any results
            product_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/game/']")
            return len(product_links) > 0
        
        # Try full search first, then fallback to simpler terms
        search_successful = search_with_query(search_query)
        if not search_successful:
            # Try without platform
            logging.info(f"Full search failed, trying without platform: {game_title}")
            search_successful = search_with_query(game_title)
            
        if not search_successful:
            # Try with key words from the title
            # For "Castlevania: The Dracula X Chronicles", try "Dracula X Chronicles"
            title_words = game_title.replace(":", "").split()
            if len(title_words) > 2:
                simplified_title = " ".join([word for word in title_words if word.lower() not in ["the", "of", "a", "an"]])
                logging.info(f"Trying simplified search: {simplified_title}")
                search_successful = search_with_query(simplified_title)
        
        # After searching, check if we found regional variants
        # If we only found US variants but need PAL/Japan, try a simplified search to find more variants
        if search_successful and region and region.upper() in ["PAL", "EUROPE", "EU", "JAPAN", "JP"]:
            product_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/game/']")
            has_regional_variant = False
            
            for link in product_links:
                href = link.get_attribute('href').lower()
                if region.upper() in ["PAL", "EUROPE", "EU"] and ("/game/pal-" in href or "/pal/" in href):
                    has_regional_variant = True
                    break
                elif region.upper() in ["JAPAN", "JP"] and ("japan" in href or "/jp/" in href):
                    has_regional_variant = True
                    break
            
            if not has_regional_variant:
                # Try simplified search to find regional variants
                title_words = game_title.replace(":", "").split()
                if len(title_words) > 2:
                    simplified_title = " ".join([word for word in title_words if word.lower() not in ["the", "of", "a", "an"]])
                    logging.info(f"No regional variants found, trying simplified search for regional variants: {simplified_title}")
                    search_with_query(simplified_title)
        
        # After searching, check if we found regional variants
        # If we only found US variants but need PAL/Japan, try a simplified search to find more variants
        if search_successful and region and region.upper() in ["PAL", "EUROPE", "EU", "JAPAN", "JP"]:
            product_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/game/']")
            has_regional_variant = False
            
            for link in product_links:
                href = link.get_attribute('href').lower()
                if region.upper() in ["PAL", "EUROPE", "EU"] and ("/game/pal-" in href or "/pal/" in href):
                    has_regional_variant = True
                    break
                elif region.upper() in ["JAPAN", "JP"] and ("japan" in href or "/jp/" in href):
                    has_regional_variant = True
                    break
            
            if not has_regional_variant:
                # Try simplified search to find regional variants
                title_words = game_title.replace(":", "").split()
                if len(title_words) > 2:
                    simplified_title = " ".join([word for word in title_words if word.lower() not in ["the", "of", "a", "an"]])
                    logging.info(f"No regional variants found, trying simplified search for regional variants: {simplified_title}")
                    search_with_query(simplified_title)
        
        # Extract pricing data from the product page
        pricing_data = {
            'loose_price': None,
            'cib_price': None, 
            'new_price': None,
            'source': 'PriceCharting',
            'product_name': None,
            'console_name': None,
            'region': region
        }
        
        # Look for search results - find the first product link
        product_link = None
        try:
            # Strategy 1: Try to find the correct regional product link and navigate to it first
            # This prioritizes individual product pages over search results extraction
            product_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/game/']")
            if product_links:
                # Try to find a link that matches our regional preference
                preferred_link = None
                fallback_link = None
                
                for link in product_links:
                    href = link.get_attribute('href')
                    link_text = link.text.strip().lower()
                    
                    # Look for regional indicators in the URL structure
                    if region and region.upper() in ["PAL", "EUROPE", "EU"]:
                        # Look for PAL/European variants - prefer main PAL URL over language-specific ones
                        href_lower = href.lower()
                        if "/game/pal-" in href_lower and not any(lang in href_lower for lang in ["/de/", "/es/", "/fr/", "/nl/", "/pt/", "/ru/"]):
                            # This is the main PAL page (not a language variant)
                            preferred_link = href
                            logging.info(f"Found main PAL variant: {href}")
                            break
                        elif "pal" in href_lower and not preferred_link:
                            # This is a PAL variant but maybe language-specific
                            preferred_link = href
                            logging.info(f"Found PAL language variant: {href}")
                        elif not fallback_link:
                            fallback_link = href  # Keep first link as fallback
                    elif region and region.upper() in ["JAPAN", "JP", "NTSC-J"]:
                        # Look for Japanese variants
                        href_lower = href.lower()
                        if any(jp_indicator in href_lower for jp_indicator in ["japan", "japanese", "jp", "ntsc-j"]):
                            preferred_link = href
                            logging.info(f"Found Japanese variant: {href}")
                            break
                        elif not fallback_link:
                            fallback_link = href  # Keep first link as fallback
                    else:
                        # Default to US or first available
                        if not fallback_link:
                            fallback_link = href
                
                # Use preferred link or fallback to first available
                product_link = preferred_link or fallback_link
                
                if product_link:
                    logging.info(f"Navigating to individual product page: {product_link}")
                    
                    # Try to navigate to the product page
                    try:
                        driver.get(product_link)
                        time.sleep(3)
                        
                        # Check if we actually reached a product page (not redirected back to search)
                        current_url = driver.current_url.lower()
                        if "/game/" in current_url and "search" not in current_url:
                            logging.info(f"Successfully reached product page: {current_url}")
                            # Continue with individual product page parsing below
                        else:
                            logging.warning(f"Product link redirected to search: {current_url}")
                            product_link = None  # Fall back to search results parsing
                    except Exception as e:
                        logging.warning(f"Failed to navigate to product page: {e}")
                        product_link = None
            
            # Strategy 2: Fallback to search results table parsing if individual page fails
            if not product_link:
                logging.info("Falling back to search results table parsing")
                search_results_table = driver.find_elements(By.CSS_SELECTOR, "table tr")
                
                selected_game_row = None
                fallback_game_row = None
                
                # Parse the search results table to find the right regional variant
                for row in search_results_table:
                    cells = row.find_elements(By.CSS_SELECTOR, "td")
                    if len(cells) >= 3:  # Should have title, platform, and price columns
                        title_cell = cells[1] if len(cells) > 1 else None
                        platform_cell = cells[2] if len(cells) > 2 else None
                        
                        if title_cell and platform_cell:
                            title_text = title_cell.text.strip().lower()
                            platform_text = platform_cell.text.strip().lower()
                            
                            # Check if this row matches our game search
                            if any(keyword in title_text for keyword in ['castlevania', 'dracula']):
                                # Prefer the regional match if we're looking for a specific region
                                if region.upper() == "PAL" and "pal" in platform_text:
                                    selected_game_row = row
                                    logging.info(f"Found PAL variant: {title_text} [{platform_text}]")
                                    break
                                elif region.upper() == "JAPAN" and ("jp" in platform_text or "japan" in platform_text):
                                    selected_game_row = row
                                    logging.info(f"Found Japan variant: {title_text} [{platform_text}]")
                                    break
                                elif region.upper() == "US" and "pal" not in platform_text and "jp" not in platform_text:
                                    selected_game_row = row
                                    logging.info(f"Found US variant: {title_text} [{platform_text}]")
                                    break
                                else:
                                    # Keep as fallback if no better match found
                                    if fallback_game_row is None:
                                        fallback_game_row = row
                                        logging.info(f"Fallback variant: {title_text} [{platform_text}]")
                
                # Use the selected row or fallback
                target_row = selected_game_row or fallback_game_row
                
                if target_row:
                    # Extract pricing data directly from the search results table
                    cells = target_row.find_elements(By.CSS_SELECTOR, "td")
                    if len(cells) >= 6:  # Should have title, platform, loose, cib, new, actions
                        try:
                            # Extract product info
                            title_cell = cells[1]
                            platform_cell = cells[2]
                            loose_cell = cells[3]
                            cib_cell = cells[4]
                            new_cell = cells[5]
                            
                            pricing_data['product_name'] = title_cell.text.strip()
                            pricing_data['console_name'] = platform_cell.text.strip()
                            
                            # Extract prices
                            for cell, price_type in [(loose_cell, 'loose_price'), (cib_cell, 'cib_price'), (new_cell, 'new_price')]:
                                price_text = cell.text.strip()
                                price_match = re.search(r'\$([0-9,]+\.?[0-9]*)', price_text)
                                if price_match:
                                    usd_price = float(price_match.group(1).replace(',', ''))
                                    pricing_data[price_type] = convert_usd_to_gbp(usd_price)
                                    pricing_data[f'{price_type}_usd'] = usd_price
                                    logging.info(f"Extracted {price_type}: ${usd_price} -> £{pricing_data[price_type]:.2f}")
                            
                            # If we successfully extracted prices from search results, we're done
                            if any(pricing_data.get(k) for k in ['loose_price', 'cib_price', 'new_price']):
                                logging.info(f"Successfully extracted prices from search results for {region} region")
                                return pricing_data
                                
                        except Exception as e:
                            logging.warning(f"Error extracting prices from search results table: {e}")
            
        except Exception as e:
            logging.warning(f"Error finding product links: {e}")
        
        # If we have a product_link, we're on an individual product page
        # If not, we already extracted from search results and should have returned
        if not product_link:
            logging.warning(f"No product found for '{game_title}' on PriceCharting")
            return None
        
        # Extract product name
        try:
            title_element = driver.find_element(By.CSS_SELECTOR, "h1")
            if title_element:
                full_title = title_element.text.strip()
                # Split title and console (format is usually "Game Name [Console]")
                if '[' in full_title and ']' in full_title:
                    game_part = full_title.split('[')[0].strip()
                    console_part = full_title.split('[')[1].split(']')[0].strip()
                    pricing_data['product_name'] = game_part
                    pricing_data['console_name'] = console_part
                else:
                    pricing_data['product_name'] = full_title
        except Exception as e:
            logging.warning(f"Could not extract product name: {e}")
        
        # Extract pricing data from the price table
        try:
            # Look for the pricing table - focus on Mid Price column as shown in screenshot
            price_table_found = False
            
            # Method 1: Look for the price guide table structure with Low/Mid/High columns
            try:
                # First, try to find the table headers to understand structure
                headers = driver.find_elements(By.CSS_SELECTOR, "th")
                header_texts = [h.text.strip() for h in headers]
                
                # Look for column indices
                low_col_idx = None
                mid_col_idx = None
                high_col_idx = None
                
                for i, header in enumerate(header_texts):
                    if 'low price' in header.lower():
                        low_col_idx = i
                    elif 'mid price' in header.lower():
                        mid_col_idx = i
                    elif 'high price' in header.lower():
                        high_col_idx = i
                
                # Find table rows and extract prices
                rows = driver.find_elements(By.CSS_SELECTOR, "tr")
                
                for row in rows:
                    cells = row.find_elements(By.CSS_SELECTOR, "td")
                    if len(cells) > max(mid_col_idx or 0, low_col_idx or 0, high_col_idx or 0):
                        row_text = row.text.lower()
                        
                        # Check if this row contains loose/complete/new pricing
                        if 'loose' in row_text or 'game only' in row_text:
                            if mid_col_idx and len(cells) > mid_col_idx:
                                try:
                                    price_text = cells[mid_col_idx].text.strip()
                                    price_match = re.search(r'\$([0-9,]+\.?[0-9]*)', price_text)
                                    if price_match:
                                        usd_price = float(price_match.group(1).replace(',', ''))
                                        pricing_data['loose_price'] = convert_usd_to_gbp(usd_price)
                                        pricing_data['loose_price_usd'] = usd_price
                                        price_table_found = True
                                except (ValueError, IndexError):
                                    pass
                        
                        elif 'complete' in row_text or 'cib' in row_text:
                            if mid_col_idx and len(cells) > mid_col_idx:
                                try:
                                    price_text = cells[mid_col_idx].text.strip()
                                    price_match = re.search(r'\$([0-9,]+\.?[0-9]*)', price_text)
                                    if price_match:
                                        usd_price = float(price_match.group(1).replace(',', ''))
                                        pricing_data['cib_price'] = convert_usd_to_gbp(usd_price)
                                        pricing_data['cib_price_usd'] = usd_price
                                        price_table_found = True
                                except (ValueError, IndexError):
                                    pass
                        
                        elif 'new' in row_text and 'newest' not in row_text and 'graded' not in row_text.lower():
                            if mid_col_idx and len(cells) > mid_col_idx:
                                try:
                                    price_text = cells[mid_col_idx].text.strip()
                                    price_match = re.search(r'\$([0-9,]+\.?[0-9]*)', price_text)
                                    if price_match:
                                        usd_price = float(price_match.group(1).replace(',', ''))
                                        pricing_data['new_price'] = convert_usd_to_gbp(usd_price)
                                        pricing_data['new_price_usd'] = usd_price
                                        price_table_found = True
                                except (ValueError, IndexError):
                                    pass
                                    
            except Exception as e:
                logging.warning(f"Method 1 (structured table) price extraction failed: {e}")
            
            # Method 2: Fallback to general price extraction if structured method fails
            if not price_table_found:
                try:
                    # Find price elements by their typical text content and structure
                    price_cells = driver.find_elements(By.CSS_SELECTOR, "td")
                    
                    for i, cell in enumerate(price_cells):
                        cell_text = cell.text.strip().lower()
                        
                        # Look for "loose" price - get next cell as price
                        if ('loose' in cell_text or cell_text == 'loose') and i + 1 < len(price_cells):
                            try:
                                price_text = price_cells[i + 1].text.strip()
                                price_match = re.search(r'\$([0-9,]+\.?[0-9]*)', price_text)
                                if price_match:
                                    usd_price = float(price_match.group(1).replace(',', ''))
                                    pricing_data['loose_price'] = convert_usd_to_gbp(usd_price)
                                    pricing_data['loose_price_usd'] = usd_price
                                    price_table_found = True
                            except (ValueError, IndexError):
                                pass
                        
                        # Look for "complete" or "cib" price
                        elif ('complete' in cell_text or 'cib' in cell_text) and i + 1 < len(price_cells):
                            try:
                                price_text = price_cells[i + 1].text.strip()
                                price_match = re.search(r'\$([0-9,]+\.?[0-9]*)', price_text)
                                if price_match:
                                    usd_price = float(price_match.group(1).replace(',', ''))
                                    pricing_data['cib_price'] = convert_usd_to_gbp(usd_price)
                                    pricing_data['cib_price_usd'] = usd_price
                                    price_table_found = True
                            except (ValueError, IndexError):
                                pass
                        
                        # Look for "new" price (but not "graded new")
                        elif ('new' in cell_text and cell_text != 'newest' and 'graded' not in cell_text.lower()) and i + 1 < len(price_cells):
                            try:
                                price_text = price_cells[i + 1].text.strip()
                                price_match = re.search(r'\$([0-9,]+\.?[0-9]*)', price_text)
                                if price_match:
                                    usd_price = float(price_match.group(1).replace(',', ''))
                                    pricing_data['new_price'] = convert_usd_to_gbp(usd_price)
                                    pricing_data['new_price_usd'] = usd_price
                                    price_table_found = True
                            except (ValueError, IndexError):
                                pass
                except Exception as e:
                    logging.warning(f"Method 2 (fallback) price extraction failed: {e}")
            
            # Method 3: Use JavaScript to extract prices if table methods fail
            if not price_table_found:
                try:
                    js_prices = driver.execute_script("""
                        var priceData = {};
                        var elements = document.querySelectorAll('*');
                        
                        for (var i = 0; i < elements.length; i++) {
                            var text = elements[i].textContent || elements[i].innerText || '';
                            
                            // Look for price patterns near specific keywords
                            if (text.includes('Loose') && text.match(/\\$[\\d,]+\\.?\\d*/)) {
                                var match = text.match(/\\$([\\d,]+\\.?\\d*)/);
                                if (match) priceData.loose = match[1];
                            }
                            if ((text.includes('Complete') || text.includes('CIB')) && text.match(/\\$[\\d,]+\\.?\\d*/)) {
                                var match = text.match(/\\$([\\d,]+\\.?\\d*)/);
                                if (match) priceData.cib = match[1];
                            }
                            // Look for "New" but exclude "Graded New"
                            if (text.includes('New') && !text.includes('Graded') && text.match(/\\$[\\d,]+\\.?\\d*/)) {
                                var match = text.match(/\\$([\\d,]+\\.?\\d*)/);
                                if (match) priceData.new = match[1];
                            }
                        }
                        
                        return priceData;
                    """)
                    
                    # Parse JavaScript results and convert to GBP
                    if js_prices.get('loose'):
                        try:
                            usd_price = float(js_prices['loose'].replace(',', ''))
                            pricing_data['loose_price'] = convert_usd_to_gbp(usd_price)
                            pricing_data['loose_price_usd'] = usd_price
                            price_table_found = True
                        except ValueError:
                            pass
                    
                    if js_prices.get('cib'):
                        try:
                            usd_price = float(js_prices['cib'].replace(',', ''))
                            pricing_data['cib_price'] = convert_usd_to_gbp(usd_price)
                            pricing_data['cib_price_usd'] = usd_price
                            price_table_found = True
                        except ValueError:
                            pass
                    
                    if js_prices.get('new'):
                        try:
                            usd_price = float(js_prices['new'].replace(',', ''))
                            pricing_data['new_price'] = convert_usd_to_gbp(usd_price)
                            pricing_data['new_price_usd'] = usd_price
                            price_table_found = True
                        except ValueError:
                            pass
                            
                except Exception as e:
                    logging.warning(f"JavaScript price extraction failed: {e}")
        
        except Exception as e:
            logging.error(f"Error extracting pricing data: {e}")
        
        # Return data if we found at least one price
        if pricing_data['loose_price'] or pricing_data['cib_price'] or pricing_data['new_price']:
            logging.info(f"Successfully scraped PriceCharting data ({region}) for '{game_title}': "
                        f"Loose: £{pricing_data['loose_price']} (${pricing_data.get('loose_price_usd', 'N/A')}), "
                        f"CIB: £{pricing_data['cib_price']} (${pricing_data.get('cib_price_usd', 'N/A')}), "
                        f"New: £{pricing_data['new_price']} (${pricing_data.get('new_price_usd', 'N/A')})")
            return pricing_data
        else:
            logging.warning(f"No pricing data found for '{game_title}' on PriceCharting ({region})")
            return None

    except Exception as e:
        logging.error(f"Error scraping PriceCharting ({region}): {e}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass