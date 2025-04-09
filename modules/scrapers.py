# scrapers.py
import time
import logging
import re 
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService

# Make sure to update this path to your chromedriver executable
driver_path = "/path/to/chromedriver"  

def scrape_barcode_lookup(barcode):
    """
    Scrapes the barcode lookup website for the game title and average price.
    Returns a tuple: (game_title, average_price)
    """
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    service = ChromeService(driver_path)
    driver = uc.Chrome(service=service, options=options)
    
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
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/115.0.0.0 Safari/537.36")

    service = ChromeService(driver_path)
    driver = uc.Chrome(service=service, options=options)

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

import re
import time
import logging
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService

def scrape_ebay_prices(game_title):
    """
    Opens eBay UK homepage, enters the game_title (which may include platform information)
    in the search box, waits for price elements to become available, and returns the first
    valid price found as a float. If no valid price is found, returns None.
    """
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    # Set a realistic user agent
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    
    service = ChromeService(driver_path)
    driver = uc.Chrome(service=service, options=options)

    try:
        driver.get("https://www.ebay.co.uk/")
        time.sleep(2)  # Allow page to load
        
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "gh-ac"))
        )
        search_box.send_keys(game_title)
        time.sleep(1)
        search_box.send_keys(Keys.RETURN)
        
        # Wait up to 10 seconds for at least one price element
        price_elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "span.s-item__price"))
        )
        
        # Iterate over elements, return the first valid price we can convert.
        for el in price_elements:
            price_text = el.text.strip()
            if not price_text:
                continue
            # Remove currency symbols and extra spaces
            price_text = price_text.replace("£", "").replace("GBP", "").strip()
            tokens = price_text.split()
            if tokens:
                try:
                    price_value = float(tokens[0].replace(",", ""))
                    logging.debug(f"Scraped eBay price text: {tokens[0]}")
                    return price_value
                except ValueError:
                    continue
        logging.warning("No valid numeric price found on eBay search page.")
        return None
    except Exception as e:
        logging.error(f"Error scraping eBay: {e}")
        return None
    finally:
        driver.quit()