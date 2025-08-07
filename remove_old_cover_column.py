#!/usr/bin/env python3
"""
Remove the old cover_image column from the games table.
We now use high_res_cover_url from SteamGridDB instead.
"""

import sqlite3
import os
import shutil
from datetime import datetime

def backup_database(db_path):
    """Create a backup of the database before making changes"""
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"✅ Database backed up to: {backup_path}")
    return backup_path

def remove_cover_image_column(db_path):
    """Remove the cover_image column from the games table"""
    print(f"🔧 Removing cover_image column from {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
        
        # 1. Get current table schema (excluding cover_image)
        cursor.execute("PRAGMA table_info(games)")
        columns = cursor.fetchall()
        
        # Filter out the cover_image column
        new_columns = [col for col in columns if col[1] != 'cover_image']
        
        print(f"📊 Current columns: {len(columns)}")
        print(f"📊 New columns: {len(new_columns)}")
        
        # 2. Create new table with updated schema
        new_table_sql = "CREATE TABLE games_new (\n"
        column_definitions = []
        column_names = []
        
        for col in new_columns:
            col_name = col[1]
            col_type = col[2]
            col_notnull = col[3]
            col_default = col[4]
            col_pk = col[5]
            
            definition = f"    {col_name} {col_type}"
            
            if col_pk:
                definition += " PRIMARY KEY"
            elif col_notnull:
                definition += " NOT NULL"
            
            if col_default is not None:
                definition += f" DEFAULT {col_default}"
            
            column_definitions.append(definition)
            column_names.append(col_name)
        
        new_table_sql += ",\n".join(column_definitions) + "\n)"
        
        print("🔨 Creating new table...")
        cursor.execute(new_table_sql)
        
        # 3. Copy data from old table to new table (excluding cover_image)
        columns_str = ", ".join(column_names)
        copy_sql = f"INSERT INTO games_new ({columns_str}) SELECT {columns_str} FROM games"
        
        print("📋 Copying data...")
        cursor.execute(copy_sql)
        
        # 4. Drop old table and rename new table
        print("🗑️  Dropping old table...")
        cursor.execute("DROP TABLE games")
        
        print("📝 Renaming new table...")
        cursor.execute("ALTER TABLE games_new RENAME TO games")
        
        # 5. Commit changes
        conn.commit()
        print("✅ Successfully removed cover_image column!")
        
        # 6. Verify the change
        cursor.execute("PRAGMA table_info(games)")
        final_columns = cursor.fetchall()
        print(f"📊 Final column count: {len(final_columns)}")
        
        # Check that cover_image is gone
        cover_image_exists = any(col[1] == 'cover_image' for col in final_columns)
        if not cover_image_exists:
            print("✅ Confirmed: cover_image column successfully removed")
        else:
            print("❌ Error: cover_image column still exists")
        
        # Show remaining columns
        print("\n📋 Remaining columns:")
        for col in final_columns:
            print(f"  • {col[1]}: {col[2]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def main():
    # Database path
    db_path = "data/games.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    
    print("🎮 Video Game Catalogue - Remove Old Cover Column")
    print("=" * 50)
    
    # Create backup
    backup_path = backup_database(db_path)
    
    try:
        # Remove the column
        remove_cover_image_column(db_path)
        print("\n🎉 Operation completed successfully!")
        print(f"💾 Backup available at: {backup_path}")
        
    except Exception as e:
        print(f"\n❌ Operation failed: {e}")
        print(f"💾 Database backup available at: {backup_path}")
        print("You can restore the backup if needed.")

if __name__ == "__main__":
    main()
