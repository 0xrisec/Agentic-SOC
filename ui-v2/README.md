# SOC AI Agent Dashboard - UI V2

A professional, Copilot-inspired user interface for the Agentic SOC system.

## Features

✨ **Modern UI Design**
- Professional dark theme inspired by GitHub Copilot
- Smooth animations and transitions
- Responsive layout for all screen sizes

🎯 **Key Capabilities**
1. **File Upload** - Drag & drop or browse to upload alert JSON files
2. **Real-time Progress** - Visual progress bar showing analysis completion
3. **Agent Pipeline** - Numbered steps showing which agent is currently running
4. **Live Activity Feed** - Real-time updates of what agents are doing
5. **Results Display** - Clear presentation of analysis results

## Quick Start

### 1. Start the Backend Server

```bash
# From the project root directory
python run.py
```

The server will start on `http://localhost:8000`

### 2. Open the UI

Navigate to: `http://localhost:8000/ui-v2/index.html`

### 3. Upload an Alert File

- Click the upload area or drag & drop your alert JSON file
- Supported format: JSON files with alert data
- Example: Use `data/alerts.json` from the project

### 4. Run Analysis

- Click the "Run Analysis" button
- Watch the progress bar and agent pipeline in real-time
- See live updates in the activity feed
- View results when complete

## UI Components

### Header
- **Logo & Title** - Branding with gradient effect
- **Status Badge** - Shows system status (Ready/Processing/Error)

### Upload Section
- **Drag & Drop Area** - Visual upload zone with hover effects
- **File Info** - Shows selected file name and size
- **Run Button** - Starts the agent analysis

### Progress Section
- **Progress Bar** - Animated bar showing 0-100% completion
- **Agent Pipeline** - 4-step visualization:
  1. Triage Agent
  2. Investigation Agent
  3. Decision Agent
  4. Response Agent
- Each step shows:
  - Step number
  - Agent name
  - Current status (Waiting/Running/Completed)
  - Visual indicator (spinner/checkmark)

### Activity Feed
- Real-time log of agent activities
- Scrollable feed with timestamps
- Color-coded by activity type

### Results Section
- Threat severity level
- Recommendations
- Suggested actions
- Analysis summary

## API Endpoints Used

The UI communicates with these backend endpoints:

- `POST /api/upload-and-run` - Upload file and start analysis
- `GET /api/status` - Poll for real-time status updates

## File Structure

```
ui-v2/
├── index.html      # Main HTML structure
├── styles.css      # Professional styling & animations
├── app.js          # Frontend logic & API integration
└── README.md       # This file
```

## Customization

### Colors
Edit CSS variables in `styles.css`:
```css
:root {
    --primary-color: #6366f1;
    --secondary-color: #8b5cf6;
    --bg-primary: #0f0f1a;
    --bg-secondary: #1a1a2e;
    /* ... more colors ... */
}
```

### Polling Interval
Adjust real-time update frequency in `app.js`:
```javascript
// Default: 500ms
pollingInterval = setInterval(async () => {
    // ... polling logic ...
}, 500);
```

## Browser Compatibility

Tested and working on:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Troubleshooting

### UI Not Loading
- Ensure backend server is running on port 8000
- Check browser console for errors
- Verify `ui-v2` folder is in project root

### File Upload Fails
- Ensure file is valid JSON format
- Check file contains alert data
- Verify backend API is accessible

### No Real-time Updates
- Check browser console for API errors
- Verify `/api/status` endpoint is responding
- Ensure CORS is properly configured

## Development

To modify the UI:

1. Edit HTML structure in `index.html`
2. Update styles in `styles.css`
3. Modify behavior in `app.js`
4. Refresh browser to see changes

No build process required - pure HTML/CSS/JS!

## Support

For issues or questions:
1. Check the main project README
2. Review backend logs
3. Inspect browser developer console
