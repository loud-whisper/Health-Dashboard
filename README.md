# Personal Health Dashboard

A fully self-hosted, offline-first dashboard to visualize your nutrition, strength training, meditation, and weight history. This tool processes raw CSV exports from your favorite health and fitness apps and renders beautiful, interactive charts entirely within your own web browser.

**Privacy First:** No cloud servers, no databases, no APIs. Your extremely personal health data never leaves your computer.

## Supported Data Sources

1. **Samsung Health:** Supports the raw `.csv` GDPR/data export zip from your phone.
   - `com.samsung.health.weight.*.csv` (Weight & Body Fat)
   - `com.samsung.shealth.exercise.*.csv` (Cardio & Meditation)
2. **Strength Training Apps (e.g., Caliber):** Supports standard `strength_workouts.csv` exports with columns for `Date`, `Exercise`, `Weight`, and `Reps`.
3. **MyFitnessPal (MFP):** Includes python scripts (`convert_mfp.py`) to parse MFP data. Note that since MFP locks CSV exports behind a premium paywall, getting your data requires a bit of manual effort (copy-pasting from the "Printable Diary" page), and the site often glitches if you try to pull more than 2 months of data at once.

## Getting Started

1. Clone or download this repository.
2. Open `health_dashboard.html` in your web browser (Chrome, Edge, Safari, Firefox).
3. Click the **Browse** buttons to select your `.csv` export files directly from your computer.
4. Click **⚡ Generate Dashboard**.

That's it! 

## Updating Your Data

When future weeks or months pass and you want to see your newest data:
1. Export a fresh CSV from your apps to your computer.
2. Open the dashboard.
3. Select those raw downloaded CSVs again and hit Generate. 

No coding or renaming files required.

## Customization

The dashboard is built using standard HTML, CSS, JavaScript, and [Chart.js](https://www.chartjs.org/). 
*   **Colors & Styles:** You can easily tweak the CSS variables in the `<style>` block at the top of the HTML file.
*   **Adding New Parsers:** Look at the `parseExercise()` or `parseWeight()` javascript functions if you want to modify this dashboard to parse data from Apple Health, Garmin, or other apps!

## Note on MyFitnessPal data

Since MyFitnessPal locks their native CSV export behind a premium subscription, extracting your historical data requires jumping through a few hoops if you don't want to pay. 

This repository provides a parser script (`convert_mfp.py` and `health_data/parse_mfp_report.py`). The general workflow is:
1. Go to the MFP website and navigate to the **Printable Diary**.
2. Select your date range. **Warning:** The MFP website frequently glitches or hangs if you try to load too much data at once. You will likely need to do this in smaller batches (e.g., 2 months at a time).
3. Copy the text from the page (or save as PDF/HTML and convert to text) and save it.
4. Run the provided Python scripts to clean this text dump into a formatted `mfp_daily_calories.csv` that the dashboard can read.

## 📱 Mobile App

This dashboard also works on your phone or tablet! There are two ways to use it:

### Android — Install the APK

1. On your Android phone, download `HealthDashboard.apk` from the [`mobile/`](mobile/) folder in this repo (or from the [direct link](mobile/HealthDashboard.apk)).
2. Open the downloaded file. Android will ask you to allow installing from unknown sources — tap **Allow** (this is safe, and you can disable it after).
3. Tap **Install**.
4. Open the app, select your CSV files, and tap **⚡ Generate Dashboard**.

> **Tip:** Transfer your CSV export files to your phone first (via USB, email, Google Drive, etc.). The app runs 100% offline once installed.

### iPhone / iPad — Add to Home Screen (PWA)

Since Apple doesn't allow sideloading apps, you can use the mobile web version instead. It looks and feels like a native app:

1. On your iPhone or iPad, open **Safari** (must be Safari, not Chrome).
2. Go to: `https://loud-whisper.github.io/Health-Dashboard/mobile/` *(or open the `mobile/index.html` file locally)*.
3. Tap the **Share** button (the square with an arrow pointing up).
4. Scroll down and tap **Add to Home Screen**.
5. Tap **Add**.
6. The app icon will appear on your home screen. Open it — it runs fullscreen, just like a real app!

### Mobile Features
- **Portrait & Landscape:** The layout automatically adapts when you rotate your device.
- **Touch-friendly:** Large tap targets for file uploads and buttons.
- **Collapsible sections:** Tap any section header to collapse/expand it.
- **Offline:** Once loaded, the app works without internet.

## Credits / Author
Created and maintained by [@loud-whisper](https://github.com/loud-whisper). 
If you find this dashboard helpful for reclaiming your personal health data from the cloud, feel free to star the repository!

## License
MIT License. Feel free to fork and customize for your own health tracking needs! By [@loud-whisper](https://github.com/loud-whisper).
