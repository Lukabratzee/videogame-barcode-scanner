#!/usr/bin/env python3
"""
Debug script with detailed logging to trace PriceCharting calls
"""
import sys
import os
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/lukabratzee/Documents/video-game-catalogue/debug_scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logger = logging.getLogger(__name__)

def test_with_detailed_logging():
    """Test with comprehensive logging"""
    
    logger.info("🔍 DETAILED DEBUG TEST STARTING")
    logger.info("=" * 60)
    
    # Test import path
    logger.info(f"Python sys.path: {sys.path}")
    
    try:
        # Import with logging
        logger.info("Attempting import from modules.scrapers...")
        from modules.scrapers import scrape_pricecharting_price, get_pricecharting_price_by_condition
        
        # Check which file was imported
        import modules.scrapers
        logger.info(f"Successfully imported from: {modules.scrapers.__file__}")
        
        # Check for version marker
        import inspect
        source = inspect.getsource(scrape_pricecharting_price)
        if "LATEST VERSION - 2025-07-27" in source:
            logger.info("✅ Using LATEST VERSION with fixes")
        else:
            logger.warning("❌ Using OLD VERSION - this is the problem!")
            
        # Test the exact same call as frontend would make
        logger.info("Testing exact frontend call pattern...")
        
        game_title = "Castlevania: The Dracula X Chronicles"  # Exact title from IGDB
        platform = "PlayStation Portable"  # Exact platform from IGDB
        region = "PAL"
        prefer_boxed = True
        
        logger.info(f"Game: {game_title}")
        logger.info(f"Platform: {platform}")
        logger.info(f"Region: {region}")
        logger.info(f"Prefer Boxed: {prefer_boxed}")
        
        # Call scraper with detailed logging
        logger.info("Calling scrape_pricecharting_price...")
        pricecharting_data = scrape_pricecharting_price(game_title, platform, region)
        
        logger.info(f"Raw scraper result: {pricecharting_data}")
        
        if pricecharting_data:
            logger.info("✅ Got PriceCharting data")
            
            # Test condition selection
            logger.info("Testing get_pricecharting_price_by_condition...")
            selected_price = get_pricecharting_price_by_condition(pricecharting_data, prefer_boxed)
            
            logger.info(f"Selected price: £{selected_price:.2f}")
            
            # Check all prices
            if pricecharting_data.get('loose_price'):
                logger.info(f"Loose: £{pricecharting_data['loose_price']:.2f} (${pricecharting_data.get('loose_price_usd', 'N/A')})")
            if pricecharting_data.get('cib_price'):
                logger.info(f"CIB: £{pricecharting_data['cib_price']:.2f} (${pricecharting_data.get('cib_price_usd', 'N/A')})")
            if pricecharting_data.get('new_price'):
                logger.info(f"New: £{pricecharting_data['new_price']:.2f} (${pricecharting_data.get('new_price_usd', 'N/A')})")
                
            # Compare with expected values
            expected_loose = 32.50
            expected_cib = 50.51  
            expected_new = 71.50
            
            actual_loose = pricecharting_data.get('loose_price', 0)
            actual_cib = pricecharting_data.get('cib_price', 0)
            actual_new = pricecharting_data.get('new_price', 0)
            
            logger.info(f"Expected vs Actual:")
            logger.info(f"  Loose: £{expected_loose} vs £{actual_loose} {'✅' if abs(actual_loose - expected_loose) < 0.01 else '❌'}")
            logger.info(f"  CIB: £{expected_cib} vs £{actual_cib} {'✅' if abs(actual_cib - expected_cib) < 0.01 else '❌'}")
            logger.info(f"  New: £{expected_new} vs £{actual_new} {'✅' if abs(actual_new - expected_new) < 0.01 else '❌'}")
            
        else:
            logger.error("❌ No data returned from scraper")
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    logger.info("✅ Detailed debug test complete")
    logger.info(f"Log written to: /Users/lukabratzee/Documents/video-game-catalogue/debug_scraper.log")

if __name__ == "__main__":
    test_with_detailed_logging()
