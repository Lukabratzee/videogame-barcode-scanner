# YouTube Trailer Integration

This document explains the YouTube trailer functionality that has been added to the Video Game Catalogue.

## Features

1. **Automatic Trailer Fetching**: When you add a new game, the system automatically searches YouTube and embeds the first relevant trailer it finds.

2. **Database Storage**: YouTube trailer URLs are stored in the `youtube_trailer_url` column of the games table.

3. **Embedded Display**: Game detail pages now show embedded YouTube trailers when available, instead of just search buttons.

4. **Manual Fetching**: You can manually fetch trailers for existing games using the included scripts.

## Database Changes

A new column `youtube_trailer_url` has been added to the games table to store the YouTube video URLs.

## Scripts

### 1. Database Migration
```bash
cd backend
python3 add_youtube_trailer_column.py
```
Adds the `youtube_trailer_url` column to the games table.

### 2. YouTube Trailer Fetcher
```bash
cd backend
python3 fetch_youtube_trailers.py
```
Fetches YouTube trailers for all games that don't have them yet.

**For a specific game:**
```bash
python3 fetch_youtube_trailers.py GAME_ID
```

### 3. Test Script
```bash
python3 test_youtube_trailer.py
```
Adds a test game and fetches its trailer to verify the system is working.

## How It Works

1. **Search Strategy**: The system searches YouTube using the format: "{game_title} {platform} trailer"

2. **Video Selection**: It automatically selects the first search result (usually the most relevant)

3. **URL Extraction**: Extracts the video ID from YouTube search results using regex patterns

4. **Storage**: Stores the full YouTube watch URL in the database

5. **Display**: The frontend extracts the video ID and embeds it using YouTube's embed player

## Frontend Changes

- **Game Detail Page**: Now shows embedded YouTube trailers when available
- **Fallback**: If no trailer is found, shows the original search button
- **Clean UI**: Removed emojis and simplified the interface as requested

## Rate Limiting

The YouTube fetcher includes built-in rate limiting (2-second delays) to be respectful to YouTube's servers and avoid being blocked.

## Error Handling

- If YouTube search fails, the system gracefully continues without a trailer
- Invalid URLs are handled with fallback display options
- Database errors are logged but don't prevent game addition

## Manual Editing

If the automatically selected trailer is incorrect, you can manually edit the `youtube_trailer_url` field in the database to point to the correct video.

## Technical Details

- Uses web scraping to search YouTube (no API key required)
- Regex-based video ID extraction from search results
- SQLite database integration
- Streamlit component for video embedding
- Error-resistant design with multiple fallback options
