# High Resolution Artwork Integration Guide

## Overview

This system integrates with **SteamGridDB** (the same service used by Steam ROM Manager on Steam Deck) to fetch high-quality artwork for your video game collection.

## What You Get

SteamGridDB provides several types of high-resolution artwork:

1. **Grid Images (Covers)**: 600x900 pixel tall covers - perfect for library display
2. **Hero Images**: Large banner-style background images
3. **Logo Images**: Transparent logo overlays
4. **Icon Images**: App-style square icons

## Setup Instructions

### 1. Get SteamGridDB API Key

1. Visit [SteamGridDB](https://www.steamgriddb.com/)
2. Create a free account or sign in
3. Go to [Profile Preferences → API](https://www.steamgriddb.com/profile/preferences/api)
4. Generate your free API key

### 2. Configure the API Key

You can set your API key in several ways:

**Option A: Environment Variable**
```bash
export STEAMGRIDDB_API_KEY="your_api_key_here"
```

**Option B: Config File**
Add to `config/config.json`:
```json
{
  "steamgriddb_api_key": "your_api_key_here"
}
```

**Option C: Command Line**
```bash
python fetch_high_res_artwork.py --api-key "your_api_key_here" --bulk
```

## Usage

### Fetch Artwork for All Games

```bash
# Navigate to backend directory
cd backend

# Process all games (will prompt for confirmation)
python fetch_high_res_artwork.py --bulk

# Process with limit (for testing)
python fetch_high_res_artwork.py --bulk --limit 10
```

### Fetch Artwork for Single Game

```bash
# Process specific game by ID
python fetch_high_res_artwork.py --game-id 123
```

## File Structure

Artwork is organized in the `data/artwork/` directory:

```
data/artwork/
├── grids/     # 600x900 tall covers
├── heroes/    # Large banner images  
├── logos/     # Transparent logos
└── icons/     # App-style icons
```

## Database Schema

The script adds these columns to your games table:

- `high_res_cover_url` - SteamGridDB grid URL
- `high_res_cover_path` - Local path to downloaded cover
- `hero_image_url` - SteamGridDB hero image URL
- `hero_image_path` - Local path to hero image
- `logo_image_url` - SteamGridDB logo URL
- `logo_image_path` - Local path to logo
- `icon_image_url` - SteamGridDB icon URL
- `icon_image_path` - Local path to icon
- `steamgriddb_id` - SteamGridDB game ID
- `artwork_last_updated` - Timestamp of last update

## Frontend Integration

The high-resolution artwork will automatically be used in:

1. **Library View**: Higher quality covers in the gallery grid
2. **Game Detail Pages**: Better cover images and additional artwork types
3. **Future Features**: Hero backgrounds, logo overlays, etc.

## Rate Limiting

- 2-second delay between requests (API best practices)
- Respectful of SteamGridDB's free tier limits
- Progress tracking for bulk operations

## Quality Comparison

**Before (IGDB)**: Typically 264x374 covers (~99KB)
**After (SteamGridDB)**: 600x900 covers (~200-500KB) with better compression

## Troubleshooting

### "No API key" Error
- Ensure you've set the API key using one of the methods above
- Verify the key is correct (no extra spaces/characters)

### "No results found" Error
- Game names sometimes don't match exactly
- The script tries "Game Title Platform" searches
- Some very obscure games might not be in SteamGridDB

### Download Failures
- Check internet connection
- Verify the artwork directory is writable
- Some artwork URLs might be temporary

## Advanced Usage

### Custom Dimensions
The script defaults to 600x900 grids, but SteamGridDB supports other sizes:
- 460x215 (banner style)
- 920x430 (large banner)
- 600x900 (tall cover - default)

### Filtering Options
SteamGridDB supports filtering:
- NSFW content (disabled by default)
- Humor/joke artwork (disabled by default)
- Style preferences (Alternate, Blurred, White Logo, etc.)

## Future Enhancements

1. **Manual Artwork Selection**: Browse and choose specific artwork
2. **Style Preferences**: Configure preferred artwork styles
3. **Background Processing**: Fetch artwork automatically for new games
4. **Artwork Management**: Tools to manage and organize downloaded artwork

## Credits

- **SteamGridDB**: Providing the high-quality artwork database
- **Steam ROM Manager**: Inspiration for the integration approach
- **Community**: Contributing artwork to SteamGridDB
