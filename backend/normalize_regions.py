#!/usr/bin/env python3
"""
Normalize existing region values in the database.

This script standardizes region values to use only: JP, NTSC, PAL
Maps various formats like "JAPAN", "JP", "Japan" to "JP", etc.
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path

# Add the project root to the path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

# Database configuration - use same logic as app.py
database_path = os.getenv("DATABASE_PATH", "").strip()
if not database_path:
    # Fallback to default path
    database_path = os.path.join(PROJECT_ROOT, "data", "games.db")

DATABASE_PATH = database_path

def normalize_region(region):
    """Normalize region values to standard codes: PAL, NTSC, JP"""
    if not region:
        return "PAL"

    region_upper = region.upper().strip()

    # Map various region formats to standard codes
    if region_upper in {"JAPAN", "JP", "JPN"}:
        return "JP"
    elif region_upper in {"NTSC", "US", "USA", "UNITED STATES", "NORTH AMERICA", "NA"}:
        return "NTSC"
    elif region_upper in {"PAL", "EU", "EUROPE", "EUROPEAN"}:
        return "PAL"
    else:
        # Default to PAL for unknown regions
        return "PAL"

def get_database_connection():
    """Get database connection"""
    return sqlite3.connect(DATABASE_PATH)

def normalize_existing_regions():
    """Normalize all existing region values in the database"""
    print("🔧 Normalizing existing region values in database...")

    conn = get_database_connection()
    cursor = conn.cursor()

    try:
        # Get all games with non-null regions
        cursor.execute("SELECT id, region FROM games WHERE region IS NOT NULL AND region != ''")
        games = cursor.fetchall()

        if not games:
            print("✅ No games found with region data to normalize")
            return

        print(f"📋 Found {len(games)} games with region data")

        # Track changes
        changes_made = 0
        region_changes = {}

        for game_id, current_region in games:
            normalized_region = normalize_region(current_region)

            if current_region != normalized_region:
                # Update the region
                cursor.execute(
                    "UPDATE games SET region = ? WHERE id = ?",
                    (normalized_region, game_id)
                )

                # Track the change
                change_key = f"{current_region} → {normalized_region}"
                region_changes[change_key] = region_changes.get(change_key, 0) + 1
                changes_made += 1

                if changes_made <= 5:  # Show first few changes
                    print(f"  🔄 Game ID {game_id}: {current_region} → {normalized_region}")

        conn.commit()

        if changes_made == 0:
            print("✅ All regions were already normalized!")
        else:
            print(f"✅ Normalized {changes_made} region entries")
            print("\n📊 Summary of changes:")
            for change, count in sorted(region_changes.items()):
                print(f"  {change}: {count} games")

    except Exception as e:
        print(f"❌ Error normalizing regions: {e}")
        conn.rollback()
    finally:
        conn.close()

def show_current_region_distribution():
    """Show the current distribution of region values in the database"""
    print("\n📊 Current region distribution:")

    conn = get_database_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT region, COUNT(*) as count
            FROM games
            WHERE region IS NOT NULL AND region != ''
            GROUP BY region
            ORDER BY count DESC
        """)

        regions = cursor.fetchall()

        if regions:
            for region, count in regions:
                normalized = normalize_region(region)
                status = "✅" if region == normalized else "🔄"
                print(f"  {status} {region}: {count} games")
        else:
            print("  No region data found")

    except Exception as e:
        print(f"❌ Error getting region distribution: {e}")
    finally:
        conn.close()

def main():
    """Main function"""
    print("🎮 Video Game Catalogue - Region Normalizer")
    print("=" * 50)

    # Validate database path
    if not os.path.exists(DATABASE_PATH):
        print(f"❌ Database not found at {DATABASE_PATH}")
        print(f"🔍 Current working directory: {os.getcwd()}")
        print(f"🔍 PROJECT_ROOT: {PROJECT_ROOT}")
        print(f"🔍 DATABASE_PATH env var: {os.getenv('DATABASE_PATH', 'Not set')}")
        sys.exit(1)

    print(f"📁 Database: {DATABASE_PATH}")

    # Show current distribution
    show_current_region_distribution()

    # Ask for confirmation
    try:
        response = input("\n🔄 Normalize all region values to standard format (JP, NTSC, PAL)? (y/N): ")
        if response.strip().lower() == 'y':
            normalize_existing_regions()
            print("\n" + "=" * 50)
            print("🎉 Region normalization complete!")
        else:
            print("ℹ️  Operation cancelled")
    except KeyboardInterrupt:
        print("\n\n🛑 Operation cancelled by user")
    except EOFError:
        # Handle non-interactive environments
        print("\n🔄 Running in non-interactive mode, proceeding with normalization...")
        normalize_existing_regions()
        print("\n" + "=" * 50)
        print("🎉 Region normalization complete!")

if __name__ == "__main__":
    main()
