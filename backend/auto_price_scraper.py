#!/usr/bin/env python3
"""
Automatic Price Scraper for Video Game Catalogue

This script automatically scrapes prices for games in your collection based on your
configured schedule and alert settings.
"""

import sqlite3
import os
import sys
import time
from datetime import datetime, timedelta
import json

# Add the backend directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def resolve_db_path() -> str:
    """Resolve database path at runtime"""
    if 'DATABASE_PATH' in os.environ and os.environ['DATABASE_PATH'].strip():
        path = os.environ['DATABASE_PATH'].strip()
        if not os.path.isabs(path):
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            path = os.path.join(base, path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, 'games.db')

def load_config():
    """Load configuration from config file"""
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    config_file = os.path.join(config_dir, 'config.json')

    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    return {}

def get_games_to_scrape():
    """Get list of games that should be scraped based on alert settings"""
    try:
        config = load_config()
        db_path = resolve_db_path()

        if not os.path.exists(db_path):
            print("❌ Database not found!")
            return []

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all games with their alert settings
        cursor.execute("""
            SELECT
                g.id, g.title, g.average_price,
                COALESCE(ags.enabled, 1) as alerts_enabled,
                COALESCE(ags.price_source, ?) as price_source,
                COALESCE(ags.price_region, 'PAL') as price_region,
                COALESCE(ags.price_drop_threshold, ?) as drop_threshold,
                COALESCE(ags.price_increase_threshold, ?) as increase_threshold,
                COALESCE(ags.alert_price_threshold, ?) as price_threshold,
                COALESCE(ags.alert_value_threshold, ?) as value_threshold
            FROM games g
            LEFT JOIN game_alert_settings ags ON g.id = ags.game_id
            WHERE COALESCE(ags.enabled, 1) = 1
            AND g.average_price IS NOT NULL
            AND g.average_price > 0
        """, (
            config.get('default_price_source', 'PriceCharting'),
            config.get('price_drop_threshold', 10.0),
            config.get('price_increase_threshold', 20.0),
            config.get('alert_price_threshold', 0.0),
            config.get('alert_value_threshold', 100.0)
        ))

        games = []
        for row in cursor.fetchall():
            game = {
                'id': row[0],
                'title': row[1],
                'current_price': row[2],
                'price_source': row[3],
                'price_region': row[4],
                'drop_threshold': row[5],
                'increase_threshold': row[6],
                'price_threshold': row[7],
                'value_threshold': row[8]
            }
            games.append(game)

        conn.close()
        return games

    except Exception as e:
        print(f"❌ Error getting games to scrape: {e}")
        return []

def scrape_game_price(game_title, price_source, price_region='PAL'):
    """Scrape price for a specific game using the specified source and region"""
    try:
        # Import scrapers
        from modules.scrapers import (
            scrape_pricecharting_price,
            scrape_ebay_prices,
            scrape_amazon_price,
            scrape_cex_price
        )

        print(f"🔍 Scraping {game_title} from {price_source} (region: {price_region})...")

        if price_source == "PriceCharting":
            result = scrape_pricecharting_price(game_title, None, price_region)
            if result and 'loose_price' in result:
                return result['loose_price']
        elif price_source == "eBay":
            results = scrape_ebay_prices(game_title)
            if results:
                # Return the lowest price found
                return min([r['price'] for r in results if 'price' in r])
        elif price_source == "Amazon":
            result = scrape_amazon_price(game_title)
            if result and 'price' in result:
                return result['price']
        elif price_source == "CeX":
            result = scrape_cex_price(game_title)
            if result and 'price' in result:
                return result['price']

        return None

    except Exception as e:
        print(f"❌ Error scraping price for {game_title}: {e}")
        return None

def update_game_price(game_id, new_price, source):
    """Update game price in database"""
    try:
        db_path = resolve_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Update the game's average_price
        cursor.execute("""
            UPDATE games
            SET average_price = ?
            WHERE id = ?
        """, (new_price, game_id))

        # Record in price history
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            INSERT INTO price_history (game_id, price, price_source, date_recorded, currency)
            VALUES (?, ?, ?, ?, ?)
        """, (game_id, new_price, source, current_date, 'GBP'))

        conn.commit()
        conn.close()

        print(f"✅ Updated price for game {game_id}: £{new_price} from {source}")
        return True

    except Exception as e:
        print(f"❌ Error updating price for game {game_id}: {e}")
        return False

def run_auto_scraping():
    """Main function to run automatic price scraping"""
    print("🚀 Starting Automatic Price Scraping...")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    config = load_config()
    if not config.get('auto_scraping_enabled', False):
        print("❌ Automatic scraping is disabled in configuration")
        return

    games = get_games_to_scrape()
    print(f"📊 Found {len(games)} games to check")

    if not games:
        print("ℹ️  No games found to scrape")
        return

    scraped_count = 0
    updated_count = 0

    for game in games:
        # Scrape the price
        new_price = scrape_game_price(game['title'], game['price_source'], game['price_region'])

        if new_price is None:
            print(f"⚠️  No price found for {game['title']}")
            continue

        scraped_count += 1

        # Check if price changed significantly
        current_price = game['current_price']
        if current_price and current_price > 0:
            change_percent = ((new_price - current_price) / current_price) * 100
            change_value = abs(new_price - current_price)

            # Check thresholds
            significant_change = (
                (change_percent <= -game['drop_threshold']) or
                (change_percent >= game['increase_threshold'])
            )

            meets_min_requirements = (
                new_price >= game['price_threshold'] and
                change_value >= game['value_threshold']
            )

            if significant_change and meets_min_requirements:
                # Update the price
                if update_game_price(game['id'], new_price, game['price_source']):
                    updated_count += 1
                    print(f"📈 Updated {game['title']}: £{current_price:.2f} → £{new_price:.2f} ({change_percent:+.1f}%)")
                else:
                    print(f"❌ Failed to update {game['title']}")
            else:
                print(f"ℹ️  Price change for {game['title']} below threshold")
        else:
            # No current price, update anyway
            if update_game_price(game['id'], new_price, game['price_source']):
                updated_count += 1
                print(f"📈 Set initial price for {game['title']}: £{new_price:.2f}")

        # Small delay to be respectful to price sources
        time.sleep(2)

    print("
✅ Auto scraping complete!"    print(f"🔍 Scraped: {scraped_count} games")
    print(f"📈 Updated: {updated_count} games")

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print("Automatic Price Scraper for Video Game Catalogue")
            print()
            print("Usage:")
            print("  python auto_price_scraper.py          # Run scraping")
            print("  python auto_price_scraper.py --help   # Show this help")
            print()
            print("Configuration:")
            print("  Set 'auto_scraping_enabled' to true in config/config.json")
            print("  Set 'auto_scraping_frequency' to 'day', 'week', or 'month'")
            print("  Configure alert thresholds in the web interface")
            return

    # Check if auto scraping is enabled
    config = load_config()
    if not config.get('auto_scraping_enabled', False):
        print("❌ Automatic scraping is disabled. Enable it in the web interface or config file.")
        return

    run_auto_scraping()

if __name__ == "__main__":
    main()
