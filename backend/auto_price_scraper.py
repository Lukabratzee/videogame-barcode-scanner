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

# Import the get_automatic_price_source function
from app import get_automatic_price_source

def resolve_db_path() -> str:
    """Resolve database path at runtime - same logic as backend app.py"""
    # Get the project root directory (one level up from backend)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Get database path from environment or use default
    database_path = os.getenv("DATABASE_PATH", "data/games.db").strip()

    # If the path is not absolute, then join with BASE_DIR (project root)
    if not os.path.isabs(database_path):
        database_path = os.path.join(BASE_DIR, database_path)

    return database_path

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
                g.id, g.title, g.platforms, g.average_price,
                ? as price_source,  -- Always use global price_source
                COALESCE(ags.price_region, 'PAL') as price_region,
                COALESCE(ags.price_drop_threshold, ?) as drop_threshold,
                COALESCE(ags.price_increase_threshold, ?) as increase_threshold,
                COALESCE(ags.alert_price_threshold, ?) as price_threshold,
                COALESCE(ags.alert_value_threshold, ?) as value_threshold
            FROM games g
            LEFT JOIN game_alert_settings ags ON g.id = ags.game_id
            WHERE ags.enabled = 1
            AND g.average_price IS NOT NULL
            AND g.average_price > 0
        """, (
            get_automatic_price_source(),  # Use automatic scraping source
            config.get('price_drop_threshold', 10.0),
            config.get('price_increase_threshold', 20.0),
            config.get('alert_price_threshold', 0.0),
            config.get('alert_value_threshold', 100.0)
        ))

        games = []
        for row in cursor.fetchall():
            # Extract the first platform from the platforms string (e.g., "PlayStation 4, Nintendo Switch" -> "PlayStation 4")
            platforms = row[2] or ""
            first_platform = platforms.split(",")[0].strip() if platforms else None

            game = {
                'id': row[0],
                'title': row[1],
                'platforms': platforms,
                'first_platform': first_platform,
                'current_price': row[3],
                'price_source': row[4],
                'price_region': row[5],
                'drop_threshold': row[6],
                'increase_threshold': row[7],
                'price_threshold': row[8],
                'value_threshold': row[9]
            }
            games.append(game)

        conn.close()
        return games

    except Exception as e:
        print(f"❌ Error getting games to scrape: {e}")
        return []

def scrape_game_price(game_title, platform, price_source, price_region='PAL'):
    """Scrape price for a specific game using the specified source and region"""
    try:
        # Build the search query with game title and platform (same as manual updates)
        search_query = game_title.strip()
        if platform:
            search_query += f" {platform}"

        print(f"🔍 Searching for: '{search_query}' on {price_source}")

        # Import scrapers
        from modules.scrapers import (
            scrape_pricecharting_price,
            scrape_ebay_prices,
            scrape_amazon_price,
            scrape_cex_price
        )

        if price_source == "PriceCharting":
            result = scrape_pricecharting_price(search_query, platform, price_region)
            if result:
                # For auto-scraping, always prioritize CiB (Complete in Box) price
                if 'cib_price' in result and result['cib_price'] is not None:
                    return result['cib_price']
                elif 'loose_price' in result and result['loose_price'] is not None:
                    return result['loose_price']
                elif 'new_price' in result and result['new_price'] is not None:
                    return result['new_price']
        elif price_source == "eBay":
            results = scrape_ebay_prices(search_query)
            if results:
                # Return the lowest price found
                return min([r['price'] for r in results if 'price' in r])
        elif price_source == "Amazon":
            result = scrape_amazon_price(search_query)
            if result and 'price' in result:
                return result['price']
        elif price_source == "CeX":
            result = scrape_cex_price(search_query)
            if result and 'price' in result:
                return result['price']

        return None
    except Exception as e:
        print(f"❌ Error scraping price for {game_title}: {e}")
        return None


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
        try:
            print(f"🔍 Scraping {game['title']} ({game['first_platform']}) from {game['price_source']} (region: {game['price_region']})...")
            new_price = scrape_game_price(game['title'], game['first_platform'], game['price_source'], game['price_region'])
            print(f"📊 scrape_game_price returned: {new_price}")
        except Exception as e:
            print(f"❌ Exception scraping {game['title']}: {e}")
            new_price = None

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
                # Send Discord notification for significant price change BEFORE updating price
                # We need to temporarily update the price_history to simulate the change for notification
                try:
                    # First, add the new price to history so check_price_change_and_alert can see the "change"
                    db_path = resolve_db_path()
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    cursor.execute("""
                        INSERT INTO price_history (game_id, price, price_source, date_recorded, currency)
                        VALUES (?, ?, ?, ?, ?)
                    """, (game['id'], new_price, game['price_source'], current_date, 'GBP'))
                    conn.commit()
                    conn.close()

                    # Now send the notification
                    from app import check_price_change_and_alert
                    check_price_change_and_alert(game['id'], new_price, game['price_source'])
                    print(f"📢 Discord notification sent for {game['title']}")

                except Exception as e:
                    print(f"❌ Failed to send Discord notification: {e}")

                # Update the game's average_price (don't add to history again since we already did)
                try:
                    db_path = resolve_db_path()
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE games
                        SET average_price = ?
                        WHERE id = ?
                    """, (new_price, game['id']))
                    conn.commit()
                    conn.close()

                    updated_count += 1
                    print(f"📈 Updated {game['title']}: £{current_price:.2f} → £{new_price:.2f} ({change_percent:+.1f}%)")
                except Exception as e:
                    print(f"❌ Failed to update {game['title']}: {e}")
            else:
                print(f"ℹ️  Price change for {game['title']} below threshold")
        else:
            # No current price, update anyway
            # Send Discord notification for new price BEFORE updating if it meets minimum requirements
            if new_price >= game['price_threshold']:
                try:
                    # For new prices, we need to add to history first so check_price_change_and_alert can work
                    db_path = resolve_db_path()
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    cursor.execute("""
                        INSERT INTO price_history (game_id, price, price_source, date_recorded, currency)
                        VALUES (?, ?, ?, ?, ?)
                    """, (game['id'], new_price, game['price_source'], current_date, 'GBP'))
                    conn.commit()
                    conn.close()

                    from app import check_price_change_and_alert
                    check_price_change_and_alert(game['id'], new_price, game['price_source'])
                    print(f"📢 Discord notification sent for new price: {game['title']}")
                except Exception as e:
                    print(f"❌ Failed to send Discord notification for new price: {e}")

            # Update the game's average_price (don't add to history again since we already did)
            try:
                db_path = resolve_db_path()
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE games
                    SET average_price = ?
                    WHERE id = ?
                """, (new_price, game['id']))
                conn.commit()
                conn.close()

                updated_count += 1
                print(f"📈 Set initial price for {game['title']}: £{new_price:.2f}")
            except Exception as e:
                print(f"❌ Failed to set initial price for {game['title']}: {e}")

        # Small delay to be respectful to price sources
        time.sleep(2)

    print("\n✅ Auto scraping complete!")
    print(f"🔍 Scraped: {scraped_count} games")
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
