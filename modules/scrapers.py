# scrapers.py - Working version with Docker isolation
import time
import logging
import re 
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_chrome_driver():
    """
    Initialize Chrome driver with COMPLETE container isolation to prevent any host browser interaction.
    """
    # Detect Docker environment
    in_docker = (os.getenv("DISPLAY") is not None or 
                 os.path.exists("/.dockerenv") or 
                 os.path.exists("/app"))
    
    if in_docker:
        logging.info("🐳 Docker environment detected - applying SMART NUCLEAR isolation")
        
        # CRITICAL: Force complete display isolation but allow Chrome sessions
        import subprocess
        
        # Kill any potential Chrome processes that might leak to host
        try:
            subprocess.run(["pkill", "-f", "chrome"], capture_output=True, timeout=5)
            subprocess.run(["pkill", "-f", "chromium"], capture_output=True, timeout=5)
        except:
            pass
        
        # Force virtual display isolation with EXTREME blocking
        os.environ["DISPLAY"] = ":99"
        os.environ["XAUTHORITY"] = "/tmp/.docker.xauth"
        os.environ["WAYLAND_DISPLAY"] = ""
        os.environ["XDG_SESSION_TYPE"] = ""
        os.environ["XDG_RUNTIME_DIR"] = "/tmp"
        os.environ["XAUTHLOCALHOSTNAME"] = "container"
        os.environ["XDG_SESSION_CLASS"] = "user"
        
        # BLOCK ALL HOST DISPLAYS - no exceptions
        for host_display in [":0", ":1", ":2", ":10", ":11"]:
            if host_display in os.environ.get("DISPLAY", ""):
                os.environ["DISPLAY"] = ":99"
                logging.warning(f"� BLOCKED host display {host_display}, forced to :99")
        
        # Complete X11 lockdown - prevent any host X11 connection
        os.environ["XORG_LOCK_DIR"] = "/tmp"
        os.environ["TMPDIR"] = "/tmp"
        os.environ["HOME"] = "/tmp"
        
        logging.info(f"🔒 SMART NUCLEAR ISOLATION - Display: {os.environ.get('DISPLAY')}")
    
    options = ChromeOptions()
    
    # MAXIMUM headless isolation
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-gpu-sandbox")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--no-first-run")
    options.add_argument("--disable-default-apps")
    options.add_argument("--window-size=1920,1080")
    
    if in_docker:
        # SMART container isolation - block host but allow Chrome functionality
        options.add_argument("--ozone-platform=headless")
        options.add_argument("--disable-x11")
        options.add_argument("--use-gl=swiftshader")
        options.add_argument("--force-device-scale-factor=1")
        
        # Host access prevention
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-translate")
        options.add_argument("--disable-features=TranslateUI,MediaRouter")
        options.add_argument("--disable-component-update")
        options.add_argument("--disable-domain-reliability")
        
        # Force container display but allow Chrome sessions to work
        options.add_argument(f"--display={os.environ.get('DISPLAY', ':99')}")
        
        # REMOVED: --single-process (causes session creation issues)
        # REMOVED: --virtual-time-budget (causes timing issues)
        # REMOVED: excessive process restrictions that break Chrome
        
        logging.info("🔒 SMART NUCLEAR ISOLATION: Host blocked, Chrome functional")
    
    # User agent for stealth
    options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    
    # Set paths for container
    if in_docker:
        options.binary_location = "/usr/bin/chromium"
        service = ChromeService("/usr/bin/chromedriver")
    else:
        service = ChromeService("/opt/homebrew/bin/chromedriver")
    
    driver = webdriver.Chrome(service=service, options=options)
    logging.info("✅ Chrome driver initialized with SMART NUCLEAR ISOLATION")
    return driver

def scrape_barcode_lookup(barcode):
    """
    Scrapes the barcode lookup website for the game title and average price.
    Returns a tuple: (game_title, average_price)
    """
    driver = None
    try:
        driver = get_chrome_driver()
        
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
        if driver:
            driver.quit()
    return game_title, average_price

def scrape_amazon_price(game_title):
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
        if driver:
            driver.quit()

def scrape_ebay_prices(game_title):
    """
    Opens eBay UK's homepage, enters the game_title in the search box,
    scrolls down to load additional results, and then collects all valid price values.
    Returns the lowest price found as a float, or None if no valid prices are found.
    """
    driver = None
    try:
        driver = get_chrome_driver()

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
        if driver:
            driver.quit()
