#!/usr/bin/env python3
"""
Quick test script to verify Chrome driver initialization works properly.
"""

import os
import sys
import logging

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_chrome_driver():
    """Test Chrome driver initialization"""
    try:
        from modules.scrapers import get_chrome_driver
        
        logging.info("Testing Chrome driver initialization...")
        
        # Test driver creation
        driver = get_chrome_driver()
        
        # Simple test - navigate to a page
        driver.get("https://www.google.com")
        
        # Get page title
        title = driver.title
        logging.info(f"Successfully loaded page with title: {title}")
        
        # Clean up
        driver.quit()
        logging.info("✅ Chrome driver test completed successfully!")
        return True
        
    except Exception as e:
        logging.error(f"❌ Chrome driver test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_chrome_driver()
    sys.exit(0 if success else 1)
