# Price Alerts Guide - Discord Notifications

## 🎯 Overview

Your Video Game Catalogue now includes a **completely free** notification system for price alerts! When you scrape prices using your existing scrapers, the system automatically detects significant price changes and sends notifications to Discord.

## 🚀 How It Works

### **Automatic Detection**
- **No API costs**: Uses your existing scraping infrastructure
- **Smart thresholds**: Only alerts on significant price changes (configurable)
- **Discord notifications**: Free webhook-based alerts
- **Per-game settings**: Custom thresholds and sources per game
- **Automatic scraping**: Scheduled background price checking

### **Notification Flow**
1. You scrape prices using existing tools (eBay, Amazon, CeX, PriceCharting)
2. System compares new prices to previous prices in your database
3. If change meets threshold → sends Discord notification
4. Supports per-game custom settings and automatic scheduling

## 🤖 Setting Up Discord Notifications

1. **Go to your Discord Server**
   - Right-click on the channel you want notifications in
   - Select "Edit Channel"

2. **Create Webhook**
   - Go to "Integrations" tab
   - Click "Create Webhook"
   - Name it "Game Price Alerts"
   - Copy the **Webhook URL** (it will look like: `https://discord.com/api/webhooks/123456789012345678/AbCdEfGhIjKlMnOpQrSt`)

3. **Configure in App**
   - Go to **🔔 Alerts** page in your app
   - Paste the webhook URL in "Discord Webhook URL"
   - Click "Save Configuration"

**Result**: Price alerts will be posted to your Discord channel!

## ⚙️ Configuring Alert Thresholds

### Global Settings (apply to all games by default)
- **Price Drop Alert Threshold**: 10% price decrease (1-50%)
- **Price Increase Alert Threshold**: 20% price increase (5-100%)
- **Minimum Price for Alerts**: £0 (only alert for games above this price)
- **Minimum Value Change**: £100 (only alert if price change is above this amount)
- **Default Price Source**: PriceCharting (can be eBay, Amazon, CeX, PriceCharting)

### Per-Game Settings (override global settings)
- **Enable/Disable**: Turn alerts on/off for specific games
- **Custom Thresholds**: Different % thresholds per game
- **Price Source**: Use different price sources per game
- **Minimum Values**: Set custom minimum price/value for alerts

**Access per-game settings**: In the Library view, click on any game to see its detail page, then look in the sidebar for "Alert Settings".

## 🔄 Automatic Price Scraping

### Setup
1. Go to **🔔 Alerts** page
2. Check "Enable Automatic Price Scraping"
3. Select frequency: **Day**, **Week**, or **Month**
4. Click "Save Configuration"

### How It Works
- **Scheduled execution**: Runs automatically based on your selected frequency
- **Respects settings**: Only scrapes games with alerts enabled
- **Uses per-game sources**: Each game uses its configured price source
- **Triggers alerts**: Automatically sends Discord notifications for significant changes

### Running Manually
```bash
cd backend
python3 auto_price_scraper.py
```

## 📊 Per-Game Alert Settings

### Accessing Settings
1. Go to **Library** view
2. Click on any game to open its detail page
3. Look for "**Alert Settings**" section in the sidebar

### Available Options
- **Enable Price Alerts**: Turn on/off alerts for this specific game
- **Price Source**: Choose which source to scrape (eBay, Amazon, CeX, PriceCharting)
- **Drop Alert %**: Custom percentage threshold for price drops
- **Increase Alert %**: Custom percentage threshold for price increases
- **Min Price (£)**: Only alert if game price is above this amount
- **Min Change (£)**: Only alert if price change is above this amount

### Example Scenarios
- **Game drops from £50 to £35** (30% decrease) → **Drop Alert**
- **Game rises from £20 to £28** (40% increase) → **Increase Alert**
- **Game changes from £40 to £42** (5% increase) → **No Alert** (below threshold)

## 🧪 Testing Your Setup

### Test Button
1. Go to **🔔 Alerts** page
2. Scroll to "Test Notifications" section
3. Customize test values or use defaults
4. Click "Send Test Notification"
5. Check your Discord channel

### What You'll Receive
```
PRICE DROP ALERT

Test Game
Old Price: £50.00
New Price: £35.00
Change: -30.0%
Source: eBay
Time: 2024-01-15 14:30:00
```

## 🔧 Advanced Configuration

### Custom Thresholds
Fine-tune alerts based on your collecting strategy:
- **Conservative**: 5% drops, 50% increases (fewer alerts)
- **Aggressive**: 15% drops, 10% increases (more alerts)

### Price Source Selection
Different sources work better for different games:
- **PriceCharting**: Good for most games, reliable data
- **eBay**: Best for rare/collectible items
- **Amazon**: Good for new releases
- **CeX**: Good for pre-owned games

## 🚨 Troubleshooting

### Discord Issues
- **Webhook URL**: Make sure you copy the entire URL including the token at the end
- **Permissions**: The webhook needs permission to post in the channel
- **Server**: You must be a server admin or have "Manage Webhooks" permission

### No Alerts Being Sent
- Check that you've scraped prices recently (alerts only trigger on new price data)
- Verify thresholds aren't too restrictive
- Test using the test button to ensure Discord webhook is working
- Check if per-game settings have disabled alerts for specific games

### Automatic Scraping Not Working
- Ensure "Enable Automatic Price Scraping" is checked
- Check that you have games with alerts enabled
- Verify the auto_price_scraper.py script can access your scrapers

## 🎮 Real-World Usage Examples

### Scenario 1: Casual Collector
- **Setup**: Discord alerts, 10% drop threshold, weekly auto-scraping
- **Result**: Get notified when games in your wishlist drop in price
- **Benefit**: Never miss a good deal on games you want

### Scenario 2: Gaming Community Server
- **Setup**: Discord webhook, 15% drop threshold, daily auto-scraping
- **Result**: Server members get notified of price drops
- **Benefit**: Community can coordinate on bulk purchases

### Scenario 3: Reseller/Flipper
- **Setup**: Discord alerts, 5% drop + 25% increase thresholds, daily auto-scraping
- **Result**: Track both buying opportunities and price trends
- **Benefit**: Optimize buying/selling decisions

## 💡 Pro Tips

1. **Start Simple**: Begin with Discord notifications and global settings
2. **Per-Game Tuning**: Use custom settings for your most valuable games
3. **Threshold Tuning**: Adjust thresholds based on your collecting habits
4. **Source Selection**: Experiment with different price sources per game
5. **Regular Testing**: Use the test button monthly to ensure everything works

## 🔄 Integration with Existing Workflow

### **Seamless Integration**
- **No workflow changes**: Your existing scraping continues unchanged
- **Automatic detection**: Works with all your current price sources
- **Database integration**: Uses your existing price_history table
- **Zero performance impact**: Lightweight background checking

### **Enhanced Experience**
- **Price history visualization**: Still shows trends in your UI
- **Manual price entry**: Also triggers alerts when you manually update prices
- **Multiple source tracking**: Alerts include which source had the price change
- **Per-game customization**: Fine-tune alerts for each game individually

## 🎯 Next Steps

1. **Set up Discord webhook** (follow the steps above)
2. **Configure your alert thresholds** based on your collecting style
3. **Test the system** using the built-in test functionality
4. **Enable automatic scraping** for hands-free price monitoring
5. **Scrape some prices** and watch the Discord alerts roll in!

## 🔒 Privacy & Security

- **Local storage**: All configuration stays on your local machine
- **No data collection**: No external services track your usage
- **Your channels**: Notifications only go to Discord channels you control
- **Secure webhooks**: Discord webhooks are encrypted in transit

---

**🎉 Congratulations!** You now have a sophisticated, free price alert system with per-game customization and automatic scraping - all powered by your existing scraping infrastructure!

**Questions?** Check the in-app help sections or test functionality for guidance.
