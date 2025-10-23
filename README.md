# CASEBOARD - PORTABLE VERSION
## McMath Woods P.A. - David W. Wells

### INSTALLATION INSTRUCTIONS

This is a portable version of your Caseboard application that can be run on any Windows computer with Python installed.

### REQUIREMENTS
- Windows 10/11
- Python 3.8 or higher (download from python.org)
- **NO ADMIN PRIVILEGES REQUIRED**

### SETUP (First Time Only)

1. **Extract this folder** to any location on your work computer
   - Example: `C:\Users\YourName\Desktop\Caseboard_Portable\`

2. **Run Setup**: Double-click `SETUP_AND_RUN.bat`
   - This will create a virtual environment
   - Install all required packages
   - Launch the application

### DAILY USE

After the first setup, simply double-click:
**`RUN_CASEBOARD.bat`**

This will start your caseboard dashboard immediately.

### OPTIONAL DISPLAYS

- **`RUN_DISPLAY_BOARD.bat`** launches the large-format Textual display board for your office TV.
- **`RUN_WEB_DASHBOARD.bat`** starts the FastAPI-powered web dashboard on http://127.0.0.1:8000 for any browser or kiosk display.

### FEATURES

✅ **Professional Case Management Dashboard**
- Case Name | County | Judge | Status | Next Deadline
- Color-coded priority deadlines
- NYSE-style stock ticker
- Blue terminal theme

✅ **Keyboard Controls**
- **E** or **A** - Add new case
- **R** - Reload cases from disk  
- **Q** - Quit application

✅ **Data Persistence**
- All cases saved in `data/cases.json`
- Automatically backs up your data

### CURRENT REFACTOR STATUS

- **Data core** – New Pydantic schema, atomic persistence, audit logging, CSV import/export, and undo stack are in place (`caseboard/schema.py`, `caseboard/data_store.py`, `caseboard/history.py`, `caseboard/csv_tools.py`).
- **Terminal UI** – Rebuilt Textual interface delivers the two-pane editor with autosave, filtering, CSV actions, and inline validation (`caseboard/app.py`).
- **Launch scripts** – `SETUP_AND_RUN.bat` and `RUN_CASEBOARD.bat` now target the `.venv` environment and surface clearer failures.
- **Web UI** – Command deck build in progress: refreshed `web/static/index.html` matches the blueprint and a new `web/static/main.js` now drives stats, practice mix, deadlines, the case drawer, and PiP controls; requires another pass to clean up legacy fragments and verify end-to-end behavior.

### PROJECT HEALTH

✓ **All systems operational!** The project has been cleaned up and optimized:
- Fixed all duplicate case IDs (18 unique cases confirmed)
- Enhanced error handling and user feedback
- Automated web asset setup
- Comprehensive documentation added

Run `python health_check.py` to verify your installation at any time.

For detailed development information, see [DEVELOPMENT.md](DEVELOPMENT.md).

### WEB COMMAND DECK BLUEPRINT

**Result**: Bloomberg-meets-Apple command deck for a 55″ TV. Keeps the `/cases` API, adds a right-side case drawer, refined copper/ink visual system, ambient lighting, and a draggable PiP for CBS News. Fonts map to the brand serif/sans pairing (Display: Argent CF, Text: Indivisible per brand guide pp.17–18; swap-in hooks noted). Poll cadence and PiP behavior match the current snapshot.

#### 1) Design rationale

- Clarity first: ledger dominates while side panels summarize risk and practice mix.
- Presence: copper accents over ink black with soft bloom/glass; brand serif for headers, crisp UI sans for data.
- Zero-scroll shell: viewport-safe at 1080p/4K with only internal scroll regions.
- Kinetic calm: slow ambient light sweep and subtle hover depth.
- Single-user tailoring: header lockup reads “McMath Woods • David W. Wells • Caseboard Command Center.”
- Continuity: consumes existing `/cases` endpoint with 60s polling (constant adjustable for `/data`).

#### 2) UI structure overview

- **Header strip** – Brandmark + title + owner line on the left; snapshot time, Refresh, Kiosk toggle, PiP toggle on the right.
- **Main grid (12-col)** – Center (8 cols) Active Case Ledger with zebra rows and detail affordances; Left (2 cols) Status Deck showing totals/attn/closed plus practice mix bars; Right (2 cols) Deadline Radar with lateness tones and day counters.
- **Detail drawer** – Right slide-in with identity, parties, stage, paralegal, focus, next due, deadlines, and quick actions (copy ID, mail paralegal, download JSON).
- **PiP panel** – Draggable CBS News live embed with sm/md/lg presets, persisted in `localStorage`.

#### 3) Production code (planned)

- `/static/index.html` – Tailwind-powered layout, Google font fallbacks (Spectral + Inter) with comments for Argent CF / Indivisible swap, ambient lighting gradients, PiP controls, and module script hook for `main.js`.
- `/static/main.js` – Polls `/cases` every 60s, renders stats/practice mix/deadlines/ledger, drives drawer + PiP interactions, preserves kiosk mode and PiP settings, exposes config constants for API path and refresh interval.
- `/static/styles.css` – Optional ambient polish (noise overlay, reduced motion guard) and asset swap notes for the brand PNGs.

#### 4) Customization notes

- **Fonts** – Replace Google fallbacks with licensed Argent CF (display) and Indivisible (text) per brand guide pp.17–18.
- **Assets** – Header mark and seal live in `/static/pngs/`; swap source filenames as needed (white lockup recommended for dark backgrounds).
- **API path** – Update `API_URL` in `main.js` if the backend serves `/data` instead of `/cases`.
- **Kiosk mode** – Fullscreen toggle exposed via the “Kiosk” button.
- **Color tuning** – Tailwind config defines `ink`, `copper`, `emerald` palette; adjust to exact brand hex values once finalized.
- **Polling** – Change `REFRESH_INTERVAL` in `main.js` to suit dashboard needs.
- **PiP** – Visibility and size persisted in `localStorage`; controls available in the PiP header.

### TROUBLESHOOTING

**Problem**: "Python is not installed"
**Solution**: Download and install Python from https://python.org

**Problem**: Virtual environment fails to create
**Solution**: Try running from a folder in your user directory (not Program Files)

**Problem**: Permission denied errors
**Solution**: Make sure you extracted to a folder you have write access to

### FILES INCLUDED

```
Caseboard_Portable/
├── SETUP_AND_RUN.bat          # First-time setup and run
├── RUN_CASEBOARD.bat          # Daily launcher
├── RUN_DISPLAY_BOARD.bat      # TV-optimized ticker board launcher
├── RUN_WEB_DASHBOARD.bat      # Web dashboard launcher (FastAPI + Tailwind)
├── run_web.py                 # Python entry point for the web dashboard
├── run.py                     # Main application launcher
├── requirements.txt           # Python dependencies
├── caseboard/                 # Application code
│   ├── app.py                 # Main application
│   ├── models.py              # Data models
│   ├── storage.py             # File handling
│   ├── widgets.py             # UI components
│   └── screens.py             # Input forms
├── web/
│   ├── main.py                # FastAPI app serving the web dashboard
│   └── static/
│       └── index.html         # Tailwind-powered client UI
└── data/
   └── cases.json             # Your case data
```

### SUPPORT

For technical issues, contact your IT department or refer to the Python installation guide at python.org.

**Health Check:** Run `python health_check.py` to verify your installation is working correctly.

**Developer Documentation:** See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed technical information.

---
**Created for McMath Woods P.A. - Professional Case Management System**