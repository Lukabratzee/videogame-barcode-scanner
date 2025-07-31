#!/usr/bin/env python3
"""
Gallery API Test Suite - Phase 1

Unit and integration tests for the Gallery API endpoints.

Author: Video Game Catalogue Team
Date: July 31, 2025
"""

import unittest
import sqlite3
import os
import sys
import tempfile
import json
from unittest.mock import patch

# Add the backend directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestGalleryAPI(unittest.TestCase):
    """Test suite for Gallery API endpoints"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database and sample data"""
        # Create a temporary database for testing
        cls.test_db_fd, cls.test_db_path = tempfile.mkstemp(suffix='.db')
        
        # Set environment variable to use test database
        os.environ['DATABASE_PATH'] = cls.test_db_path
        
        # Import gallery_api after setting the database path
        from gallery_api import app, get_db_connection
        cls.app = app
        cls.app.config['TESTING'] = True
        cls.client = app.test_client()
        
        # Set up test database schema
        cls._create_test_database()
        cls._seed_test_data()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test database"""
        os.close(cls.test_db_fd)
        os.unlink(cls.test_db_path)
        if 'DATABASE_PATH' in os.environ:
            del os.environ['DATABASE_PATH']
    
    @classmethod
    def _create_test_database(cls):
        """Create test database with the required schema"""
        conn = sqlite3.connect(cls.test_db_path)
        cursor = conn.cursor()
        
        # Create games table
        cursor.execute('''
        CREATE TABLE games (
            id INTEGER PRIMARY KEY,
            title TEXT,
            cover_image TEXT,
            description TEXT,
            publisher TEXT,
            platforms TEXT,
            genres TEXT,
            series TEXT,
            release_date TEXT,
            average_price REAL
        )
        ''')
        
        # Create gallery tables (simplified version)
        cursor.execute('''
        CREATE TABLE game_gallery_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            trailer_url TEXT,
            gamefaqs_url TEXT,
            powerpyx_url TEXT,
            metacritic_url TEXT,
            steam_url TEXT,
            psn_url TEXT,
            xbox_url TEXT,
            nintendo_url TEXT,
            display_priority INTEGER DEFAULT 0,
            gallery_enabled BOOLEAN DEFAULT 1,
            completion_status TEXT DEFAULT 'not_started',
            personal_rating INTEGER,
            play_time_hours REAL,
            date_acquired TEXT,
            date_started TEXT,
            date_completed TEXT,
            notes TEXT,
            favorite BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (game_id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE game_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_name TEXT NOT NULL UNIQUE,
            tag_color TEXT DEFAULT '#6366f1',
            tag_description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            display_order INTEGER DEFAULT 0
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE game_tag_associations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (game_id, tag_id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    @classmethod
    def _seed_test_data(cls):
        """Insert test data into the database"""
        conn = sqlite3.connect(cls.test_db_path)
        cursor = conn.cursor()
        
        # Insert test games
        test_games = [
            (1, "Super Mario Bros.", "mario.jpg", "Classic platformer", "Nintendo", "NES", "Platform", "Super Mario", "1985-09-13", 25.50),
            (2, "The Legend of Zelda", "zelda.jpg", "Adventure RPG", "Nintendo", "NES", "Adventure,RPG", "Zelda", "1986-02-21", 35.00),
            (3, "Tetris", "tetris.jpg", "Puzzle game", "Nintendo", "Game Boy", "Puzzle", "", "1989-06-14", 15.00),
            (4, "Final Fantasy VII", "ff7.jpg", "JRPG classic", "Square", "PlayStation", "RPG", "Final Fantasy", "1997-01-31", 45.00),
        ]
        
        for game in test_games:
            cursor.execute('''
            INSERT INTO games (id, title, cover_image, description, publisher, platforms, genres, series, release_date, average_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', game)
        
        # Insert test tags
        test_tags = [
            (1, "Action", "#ef4444", "High-energy games"),
            (2, "RPG", "#8b5cf6", "Role-playing games"),
            (3, "Puzzle", "#f59e0b", "Brain-teasing games"),
            (4, "Completed", "#22c55e", "Finished games"),
            (5, "Favorite", "#e11d48", "Personal favorites"),
        ]
        
        for tag in test_tags:
            cursor.execute('''
            INSERT INTO game_tags (id, tag_name, tag_color, tag_description)
            VALUES (?, ?, ?, ?)
            ''', tag)
        
        # Insert gallery metadata for some games
        cursor.execute('''
        INSERT INTO game_gallery_metadata 
        (game_id, completion_status, personal_rating, favorite, trailer_url)
        VALUES (1, 'completed', 10, 1, 'https://youtube.com/watch?v=mario')
        ''')
        
        cursor.execute('''
        INSERT INTO game_gallery_metadata 
        (game_id, completion_status, personal_rating, favorite)
        VALUES (2, 'in_progress', 9, 1)
        ''')
        
        # Insert tag associations
        cursor.execute('INSERT INTO game_tag_associations (game_id, tag_id) VALUES (1, 4)')  # Mario - Completed
        cursor.execute('INSERT INTO game_tag_associations (game_id, tag_id) VALUES (1, 5)')  # Mario - Favorite
        cursor.execute('INSERT INTO game_tag_associations (game_id, tag_id) VALUES (2, 2)')  # Zelda - RPG
        cursor.execute('INSERT INTO game_tag_associations (game_id, tag_id) VALUES (3, 3)')  # Tetris - Puzzle
        cursor.execute('INSERT INTO game_tag_associations (game_id, tag_id) VALUES (4, 2)')  # FF7 - RPG
        
        conn.commit()
        conn.close()
    
    def test_get_gallery_games_basic(self):
        """Test basic gallery games endpoint"""
        response = self.client.get('/api/gallery/games')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('games', data['data'])
        self.assertIn('pagination', data['data'])
        
        # Should have 4 test games
        self.assertEqual(len(data['data']['games']), 4)
        
        # Check pagination info
        pagination = data['data']['pagination']
        self.assertEqual(pagination['current_page'], 1)
        self.assertEqual(pagination['total_count'], 4)
        self.assertEqual(pagination['per_page'], 24)
    
    def test_get_gallery_games_with_filters(self):
        """Test gallery games endpoint with filters"""
        # Test platform filter
        response = self.client.get('/api/gallery/games?platform=NES')
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']['games']), 2)  # Mario and Zelda
        
        # Test completion filter
        response = self.client.get('/api/gallery/games?completion=completed')
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']['games']), 1)  # Only Mario
        
        # Test favorite filter
        response = self.client.get('/api/gallery/games?favorite=true')
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']['games']), 2)  # Mario and Zelda
        
        # Test search filter
        response = self.client.get('/api/gallery/games?search=Mario')
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']['games']), 1)  # Only Mario
    
    def test_get_gallery_games_pagination(self):
        """Test gallery games pagination"""
        # Test with limit
        response = self.client.get('/api/gallery/games?limit=2')
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']['games']), 2)
        
        pagination = data['data']['pagination']
        self.assertEqual(pagination['per_page'], 2)
        self.assertEqual(pagination['total_pages'], 2)  # 4 games / 2 per page
        self.assertTrue(pagination['has_next'])
        self.assertFalse(pagination['has_prev'])
        
        # Test page 2
        response = self.client.get('/api/gallery/games?limit=2&page=2')
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']['games']), 2)
        
        pagination = data['data']['pagination']
        self.assertEqual(pagination['current_page'], 2)
        self.assertFalse(pagination['has_next'])
        self.assertTrue(pagination['has_prev'])
    
    def test_get_gallery_game_detail(self):
        """Test individual game detail endpoint"""
        # Test existing game
        response = self.client.get('/api/gallery/game/1')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        game = data['data']
        self.assertEqual(game['id'], 1)
        self.assertEqual(game['title'], "Super Mario Bros.")
        self.assertIn('gallery_metadata', game)
        self.assertIn('tags', game)
        
        # Check gallery metadata
        metadata = game['gallery_metadata']
        self.assertEqual(metadata['completion_status'], 'completed')
        self.assertEqual(metadata['personal_rating'], 10)
        self.assertTrue(metadata['favorite'])
        self.assertEqual(metadata['trailer_url'], 'https://youtube.com/watch?v=mario')
        
        # Check tags
        tags = game['tags']
        self.assertEqual(len(tags), 2)  # Completed and Favorite
        tag_names = [tag['name'] for tag in tags]
        self.assertIn('Completed', tag_names)
        self.assertIn('Favorite', tag_names)
        
        # Test non-existent game
        response = self.client.get('/api/gallery/game/999')
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    def test_get_gallery_filters(self):
        """Test gallery filters endpoint"""
        response = self.client.get('/api/gallery/filters')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        filters = data['data']
        
        # Check platforms
        self.assertIn('platforms', filters)
        platforms = filters['platforms']
        self.assertIn('NES', platforms)
        self.assertIn('Game Boy', platforms)
        self.assertIn('PlayStation', platforms)
        
        # Check completion statuses
        self.assertIn('completion_statuses', filters)
        statuses = filters['completion_statuses']
        self.assertEqual(len(statuses), 4)
        status_values = [status['value'] for status in statuses]
        self.assertIn('not_started', status_values)
        self.assertIn('completed', status_values)
        
        # Check tags
        self.assertIn('tags', filters)
        tags = filters['tags']
        self.assertGreaterEqual(len(tags), 5)  # At least our test tags
        
        # Check sort options
        self.assertIn('sort_options', filters)
        sort_options = filters['sort_options']
        self.assertGreater(len(sort_options), 0)

def run_tests():
    """Run the test suite"""
    print("🧪 Running Gallery API Test Suite...")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestGalleryAPI)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    if result.wasSuccessful():
        print(f"\n✅ All {result.testsRun} tests passed!")
        return True
    else:
        print(f"\n❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)")
        return False

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
