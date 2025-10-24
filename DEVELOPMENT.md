# Caseboard Development Guide

## Project Structure

```
Caseboard_Portable/
├── caseboard/              # Core application modules
│   ├── app.py             # Main Textual UI application
│   ├── models.py          # Legacy data models (dataclasses)
│   ├── schema.py          # Pydantic schema definitions (v2)
│   ├── data_store.py      # Data persistence layer with locking
│   ├── storage.py         # Legacy storage utilities
│   ├── history.py         # Undo/redo functionality
│   ├── csv_tools.py       # CSV import/export
│   ├── constants.py       # Shared constants and case types
│   ├── exceptions.py      # Custom exception classes
│   ├── display.py         # Display board application
│   ├── screens.py         # Input form screens
│   ├── widgets.py         # Custom UI widgets
│   └── stocks.py          # Stock ticker integration
├── web/                   # Web dashboard
│   ├── main.py            # FastAPI application
│   └── static/
│       ├── index.html     # Dashboard UI (Tailwind CSS)
│       ├── main.js        # Client-side logic
│       └── pngs/          # Brand assets (auto-generated)
├── data/                  # Data directory
│   ├── cases.json         # Main case database
│   ├── backups/           # Automatic backups
│   └── migrations/        # Schema migration logs
├── pngs/                  # Source brand assets
│   ├── brandmark/         # Logo marks
│   ├── horizontal/        # Horizontal layouts
│   └── vertical/          # Vertical layouts
├── run.py                 # Main terminal UI entry point
├── run_web.py             # Web dashboard entry point
├── run_display.py         # Display board entry point
├── setup_web_assets.py    # Web asset preparation script
└── requirements.txt       # Python dependencies
```

## Getting Started

### First Time Setup

**Windows:**
```batch
SETUP_AND_RUN.bat
```

**Linux/Mac:**
```bash
bash auto_setup_and_run.sh
```

This will:
1. Create a virtual environment in `.venv/`
2. Install all required dependencies
3. Setup web assets
4. Launch the terminal UI

### Daily Use

**Terminal UI (Main Dashboard):**
```batch
RUN_CASEBOARD.bat
```

**Web Dashboard:**
```batch
RUN_WEB_DASHBOARD.bat
```
Then open http://127.0.0.1:8000 in your browser.

**Display Board (TV/Kiosk Mode):**
```batch
RUN_DISPLAY_BOARD.bat
```

## Data Management

### Case Data Structure

Cases are stored in `data/cases.json` with the following schema:

```json
{
  "schema_version": 2,
  "version": 1,
  "saved_at": "2025-10-23T22:59:47.198415Z",
  "cases": [
    {
      "id": "uuid-string",
      "case_number": "60CV-25-12762",
      "case_name": "Willis v. Doe",
      "case_type": "Personal Injury",
      "stage": "Discovery",
      "attention": "waiting",
      "status": "open",
      "paralegal": "Name",
      "current_task": "Description",
      "county": "Pulaski",
      "division": "12th",
      "judge": "Connors",
      "opposing_counsel": "",
      "opposing_firm": "",
      "deadlines": [
        {
          "due_date": "2025-11-17",
          "description": "Task description",
          "resolved": false
        }
      ],
      "sol_date": null
    }
  ]
}
```

### Backups

Automatic backups are created in `data/backups/` whenever the file is loaded. Files are named with timestamps: `cases-YYYYMMDD-HHMMSS.json`

### Data Integrity

- Each case must have a unique `id` (UUID)
- The application uses file locking to prevent concurrent modifications
- Schema migrations are automatically applied when loading older data

## Case Types

The following case types are predefined:

- Personal Injury
- MVA (Motor Vehicle Accident)
- Wrongful Death
- Catastrophic Injury
- Medical Malpractice
- Divorce
- Environmental
- Other

Colors are automatically assigned based on case type for visual differentiation in the UI.

## Development

### Adding New Features

1. **Terminal UI Changes:** Edit `caseboard/app.py`
2. **Web Dashboard Changes:** Edit `web/static/index.html` and `web/static/main.js`
3. **Data Schema Changes:** Update `caseboard/schema.py` and increment `APP_SCHEMA_VERSION`
4. **New API Endpoints:** Add to `web/main.py`

### Code Style

- Use type hints (Python 3.8+ syntax)
- Follow PEP 8 conventions
- Use Pydantic for data validation
- Prefer dataclasses or Pydantic models over plain dictionaries

### Testing Changes

After making changes:

1. Verify the terminal UI: `python run.py`
2. Verify the web dashboard: `python run_web.py`
3. Check data integrity: Ensure cases.json is valid JSON
4. Test with your existing case data

## Troubleshooting

### Common Issues

**"Python is not installed"**
- Install Python 3.8 or higher from https://python.org
- Ensure Python is in your PATH

**Virtual environment fails to create**
- Try running from a user directory (not Program Files)
- Check you have write permissions

**Web dashboard shows missing images**
- Run `python setup_web_assets.py` to copy PNG files
- Or run `SETUP_AND_RUN.bat` which does this automatically

**Cases not loading**
- Check `data/cases.json` is valid JSON
- Look for backups in `data/backups/` if the file is corrupted
- The application will create an empty file if none exists

**Duplicate case IDs**
- This was fixed in the latest cleanup
- If you encounter this, each case should have a unique UUID

### Log Files

Error messages are displayed in the console. For web dashboard:
- FastAPI logs show in the console where you ran `RUN_WEB_DASHBOARD.bat`
- Browser console (F12) shows client-side errors

## Architecture Notes

### Schema Version 2

The current schema (version 2) includes:
- UUID-based case IDs
- Pydantic validation
- Atomic file writes with locking
- Automatic backups
- Migration support

### Terminal UI (Textual)

The terminal UI is built with [Textual](https://textual.textualize.io/), providing:
- Rich, interactive terminal interface
- Keyboard shortcuts
- Form-based data entry
- Real-time updates

### Web Dashboard (FastAPI + Vanilla JS)

The web dashboard provides:
- REST API via FastAPI
- Tailwind CSS for styling
- Vanilla JavaScript (no frameworks)
- Real-time polling (60-second refresh)
- Picture-in-Picture CBS News embed
- LocalStorage for preferences

## Maintenance

### Regular Tasks

1. **Check backups:** Review `data/backups/` periodically
2. **Update dependencies:** Run `pip install --upgrade -r requirements.txt` in your venv
3. **Review case data:** Ensure no duplicate IDs or data corruption

### Before Major Changes

1. Create a backup of the entire `data/` directory
2. Test changes in a separate environment
3. Verify existing cases load correctly after changes

## Credits

Created for McMath Woods P.A. - Professional Case Management System
