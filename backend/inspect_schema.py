#!/usr/bin/env python3
"""
Inspect the current database schema and show table structures
"""
import sqlite3
import os

# Use DATABASE_PATH environment variable if set, otherwise use local directory
if 'DATABASE_PATH' in os.environ:
    db_path = os.environ['DATABASE_PATH']
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, 'games.db')

print(f"📍 Database path: {db_path}")
print(f"📊 Database exists: {os.path.exists(db_path)}")

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print(f"\n📋 Tables in database: {len(tables)}")
    
    for table in tables:
        table_name = table[0]
        print(f"\n🗃️  Table: {table_name}")
        
        # Get table schema
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        print("   Columns:")
        for col in columns:
            col_id, name, data_type, not_null, default_value, is_pk = col
            pk_indicator = " (PRIMARY KEY)" if is_pk else ""
            null_indicator = " NOT NULL" if not_null else ""
            default_indicator = f" DEFAULT {default_value}" if default_value is not None else ""
            print(f"     • {name}: {data_type}{pk_indicator}{null_indicator}{default_indicator}")
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        count = cursor.fetchone()[0]
        print(f"   📈 Row count: {count}")
    
    conn.close()
else:
    print("❌ Database file not found!")
