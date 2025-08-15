#!/usr/bin/env python3
"""
Gallery API Endpoints - Phase 1

Provides REST API endpoints for the Gallery feature:
- GET /api/gallery/games - Paginated gallery view with filters
- GET /api/gallery/game/{id} - Individual game detail with gallery metadata
- PUT /api/gallery/game/{id}/metadata - Update gallery-specific metadata
- GET /api/gallery/filters - Available filter options
- GET /api/gallery/tags - Tag management
- POST /api/gallery/tags - Create new tags

Author: Video Game Catalogue Team
Date: July 31, 2025
"""

from flask import Flask, request, jsonify
import sqlite3
import os
from datetime import datetime
import json
import unicodedata

# Text normalization helper
def normalize_for_search(text):
    """
    Normalize text for search by removing accents and special characters.
    This allows 'Pokemon' to match 'Pokémon', etc.
    """
    if not text:
        return ""
    
    # Normalize unicode characters (NFD = decomposed form)
    normalized = unicodedata.normalize('NFD', text)
    
    # Remove combining characters (accents)
    ascii_text = ''.join(char for char in normalized 
                        if unicodedata.category(char) != 'Mn')
    
    # Convert to lowercase for case-insensitive search
    return ascii_text.lower()

# Database connection helper
def get_db_connection():
    """Get database connection using environment variable or default path"""
    if 'DATABASE_PATH' in os.environ:
        db_path = os.environ['DATABASE_PATH']
    else:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(BASE_DIR, 'games.db')
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
    return conn

def serialize_game_with_metadata(game_row, metadata_row=None, tags=None):
    """Convert database rows to JSON-serializable dictionary"""
    game_dict = {
        'id': game_row['id'],
        'title': game_row['title'],
        'cover_image': game_row['cover_image'],
        'description': game_row['description'],
        'publisher': game_row['publisher'],
        'platforms': game_row['platforms'].split(',') if game_row['platforms'] else [],
        'genres': game_row['genres'].split(',') if game_row['genres'] else [],
        'series': game_row['series'],
        'release_date': game_row['release_date'],
        'average_price': game_row['average_price'],
        'region': game_row.get('region', 'PAL')  # Default to PAL if not set
    }
    
    # Add gallery metadata if available
    if metadata_row:
        game_dict['gallery_metadata'] = {
            'trailer_url': metadata_row['trailer_url'],
            'gamefaqs_url': metadata_row['gamefaqs_url'],
            'powerpyx_url': metadata_row['powerpyx_url'],
            'metacritic_url': metadata_row['metacritic_url'],
            'steam_url': metadata_row['steam_url'],
            'psn_url': metadata_row['psn_url'],
            'xbox_url': metadata_row['xbox_url'],
            'nintendo_url': metadata_row['nintendo_url'],
            'display_priority': metadata_row['display_priority'],
            'gallery_enabled': bool(metadata_row['gallery_enabled']),
            'completion_status': metadata_row['completion_status'],
            'personal_rating': metadata_row['personal_rating'],
            'play_time_hours': metadata_row['play_time_hours'],
            'date_acquired': metadata_row['date_acquired'],
            'date_started': metadata_row['date_started'],
            'date_completed': metadata_row['date_completed'],
            'notes': metadata_row['notes'],
            'favorite': bool(metadata_row['favorite']),
            'created_at': metadata_row['created_at'],
            'updated_at': metadata_row['updated_at']
        }
    else:
        # Default metadata if none exists
        game_dict['gallery_metadata'] = {
            'gallery_enabled': True,
            'completion_status': 'not_started',
            'favorite': False,
            'display_priority': 0
        }
    
    # Add tags if provided
    if tags:
        game_dict['tags'] = tags
    
    return game_dict

# Gallery API Routes
app = Flask(__name__)

@app.route('/api/gallery/games', methods=['GET'])
def get_gallery_games():
    """
    Get paginated list of games for gallery view with optional filters
    
    Query Parameters:
    - page: Page number (default: 1)
    - limit: Items per page (default: 24)
    - sort: Sort order (title_asc, title_desc, date_asc, date_desc, rating_desc, etc.)
    - platform: Filter by platform
    - completion: Filter by completion status
    - favorite: Filter favorites only (true/false)
    - genre: Filter by individual genre (e.g., Adventure, Action, RPG)
    - region: Filter by region (PAL, NTSC, JP)
    - search: Search query for title
    """
    try:
        # Parse query parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 24))
        sort_order = request.args.get('sort', 'title_asc')
        platform_filter = request.args.get('platform')
        completion_filter = request.args.get('completion')
        favorite_filter = request.args.get('favorite')
        genre_filter = request.args.get('genre')  # Changed from tag_filter to genre_filter
        region_filter = request.args.get('region')  # New region filter
        search_query = request.args.get('search')
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Build the query (simplified - removed tag joins since we're using genre filtering)
        base_query = '''
        SELECT DISTINCT g.*, gm.* 
        FROM games g
        LEFT JOIN game_gallery_metadata gm ON g.id = gm.game_id
        WHERE g.id != -1  -- Exclude placeholder
        '''
        
        count_query = '''
        SELECT COUNT(DISTINCT g.id) 
        FROM games g
        LEFT JOIN game_gallery_metadata gm ON g.id = gm.game_id
        WHERE g.id != -1  -- Exclude placeholder
        '''
        
        query_params = []
        
        # Add filters
        if platform_filter:
            base_query += " AND g.platforms LIKE ?"
            count_query += " AND g.platforms LIKE ?"
            query_params.append(f"%{platform_filter}%")
            
        if completion_filter:
            base_query += " AND (gm.completion_status = ? OR (gm.completion_status IS NULL AND ? = 'not_started'))"
            count_query += " AND (gm.completion_status = ? OR (gm.completion_status IS NULL AND ? = 'not_started'))"
            query_params.extend([completion_filter, completion_filter])
            
        if favorite_filter and favorite_filter.lower() == 'true':
            base_query += " AND gm.favorite = 1"
            count_query += " AND gm.favorite = 1"
            
        if genre_filter:
            base_query += " AND g.genres LIKE ?"
            count_query += " AND g.genres LIKE ?"
            query_params.append(f"%{genre_filter}%")
            
        if region_filter:
            base_query += " AND UPPER(IFNULL(g.region, 'PAL')) = ?"
            count_query += " AND UPPER(IFNULL(g.region, 'PAL')) = ?"
            query_params.append(region_filter.upper())
            
        if search_query:
            # Enhanced search with special character normalization
            normalized_search = normalize_for_search(search_query)
            
            # Search using both the original term and the accent-stripped version
            search_condition = """ AND (
                LOWER(g.title) LIKE ? OR 
                LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                    g.title, 'é', 'e'), 'è', 'e'), 'ê', 'e'), 'ë', 'e'), 
                    'á', 'a'), 'à', 'a'), 'ä', 'a'), 'â', 'a'),
                    'ó', 'o'), 'ò', 'o')) LIKE ?
            )"""
            base_query += search_condition
            count_query += search_condition
            query_params.extend([f"%{search_query.lower()}%", f"%{normalized_search}%"])
        
        # Add sorting
        sort_mapping = {
            'title_asc': 'g.title ASC',
            'title_desc': 'g.title DESC',
            'date_asc': 'g.release_date ASC',
            'date_desc': 'g.release_date DESC',
            'rating_desc': 'gm.personal_rating DESC NULLS LAST',
            'rating_asc': 'gm.personal_rating ASC NULLS LAST',
            'price_desc': 'g.average_price DESC NULLS LAST',
            'price_asc': 'g.average_price ASC NULLS LAST',
            'priority_desc': 'gm.display_priority DESC NULLS LAST'
        }
        
        order_clause = sort_mapping.get(sort_order, 'g.title ASC')
        base_query += f" ORDER BY {order_clause}"
        
        # Add pagination
        base_query += " LIMIT ? OFFSET ?"
        pagination_params = query_params + [limit, offset]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute(count_query, query_params)
        total_count = cursor.fetchone()[0]
        
        # Get games
        cursor.execute(base_query, pagination_params)
        game_rows = cursor.fetchall()
        
        # Process results (no longer fetching tags separately)
        games = []
        for row in game_rows:
            # Convert to dictionary
            game_dict = serialize_game_with_metadata(row, row)
            games.append(game_dict)
        
        conn.close()
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit  # Ceiling division
        has_next = page < total_pages
        has_prev = page > 1
        
        return jsonify({
            'success': True,
            'data': {
                'games': games,
                'pagination': {
                    'current_page': page,
                    'total_pages': total_pages,
                    'total_count': total_count,
                    'per_page': limit,
                    'has_next': has_next,
                    'has_prev': has_prev
                },
                'filters_applied': {
                    'platform': platform_filter,
                    'completion': completion_filter,
                    'favorite': favorite_filter,
                    'genre': genre_filter,
                    'region': region_filter,
                    'search': search_query,
                    'sort': sort_order
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/gallery/game/<int:game_id>', methods=['GET'])
def get_gallery_game_detail(game_id):
    """Get detailed information for a single game including all gallery metadata"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get game and metadata
        cursor.execute('''
        SELECT g.*, gm.*
        FROM games g
        LEFT JOIN game_gallery_metadata gm ON g.id = gm.game_id
        WHERE g.id = ?
        ''', (game_id,))
        
        game_row = cursor.fetchone()
        
        if not game_row:
            return jsonify({
                'success': False,
                'error': 'Game not found'
            }), 404
        
        # Get tags
        cursor.execute('''
        SELECT gt.id, gt.tag_name, gt.tag_color, gt.tag_description
        FROM game_tags gt
        JOIN game_tag_associations gta ON gt.id = gta.tag_id
        WHERE gta.game_id = ?
        ORDER BY gt.tag_name
        ''', (game_id,))
        
        tag_rows = cursor.fetchall()
        tags = [{
            'id': tag['id'], 
            'name': tag['tag_name'], 
            'color': tag['tag_color'],
            'description': tag['tag_description']
        } for tag in tag_rows]
        
        conn.close()
        
        # Serialize game data
        game_dict = serialize_game_with_metadata(game_row, game_row, tags)
        
        return jsonify({
            'success': True,
            'data': game_dict
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/gallery/filters', methods=['GET'])
def get_gallery_filters():
    """Get available filter options for the gallery"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get unique platforms
        cursor.execute('''
        SELECT DISTINCT platforms 
        FROM games 
        WHERE id != -1 AND platforms IS NOT NULL AND platforms != ''
        ''')
        
        platform_rows = cursor.fetchall()
        platforms = []
        for row in platform_rows:
            if row['platforms']:
                # Split comma-separated platforms and flatten
                for platform in row['platforms'].split(','):
                    platform = platform.strip()
                    if platform and platform not in platforms:
                        platforms.append(platform)
        
        platforms.sort()
        
        # Get unique genres (split individual genres instead of tag-like structure)
        cursor.execute('''
        SELECT DISTINCT genres 
        FROM games 
        WHERE id != -1 AND genres IS NOT NULL AND genres != ''
        ''')
        
        genre_rows = cursor.fetchall()
        genres = []
        for row in genre_rows:
            if row['genres']:
                # Split comma-separated genres and flatten
                for genre in row['genres'].split(','):
                    genre = genre.strip()
                    if genre and genre not in genres:
                        genres.append(genre)
        
        genres.sort()
        
        # Get unique regions
        cursor.execute('''
        SELECT DISTINCT IFNULL(region, 'PAL') as region
        FROM games 
        WHERE id != -1
        ''')
        
        region_rows = cursor.fetchall()
        regions = sorted(list(set([row['region'] for row in region_rows if row['region']])))
        
        # Ensure standard regions are available even if no games exist
        if 'PAL' not in regions:
            regions.append('PAL')
        if 'NTSC' not in regions:
            regions.append('NTSC')
        if 'JP' not in regions:
            regions.append('JP')
        regions.sort()
        
        # Get completion statuses
        completion_statuses = [
            {'value': 'not_started', 'label': 'Not Started'},
            {'value': 'in_progress', 'label': 'In Progress'},
            {'value': 'completed', 'label': 'Completed'},
            {'value': 'abandoned', 'label': 'Abandoned'}
        ]
        
        # Remove tags section - we're using genres instead
        
        # Get sort options
        sort_options = [
            {'value': 'title_asc', 'label': 'Title (A-Z)'},
            {'value': 'title_desc', 'label': 'Title (Z-A)'},
            {'value': 'date_desc', 'label': 'Release Date (Newest)'},
            {'value': 'date_asc', 'label': 'Release Date (Oldest)'},
            {'value': 'rating_desc', 'label': 'Personal Rating (High)'},
            {'value': 'rating_asc', 'label': 'Personal Rating (Low)'},
            {'value': 'price_desc', 'label': 'Price (High)'},
            {'value': 'price_asc', 'label': 'Price (Low)'},
            {'value': 'priority_desc', 'label': 'Display Priority'}
        ]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'platforms': platforms,
                'genres': genres,
                'regions': regions,
                'completion_statuses': completion_statuses,
                'sort_options': sort_options
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Run on different port to avoid conflicts
