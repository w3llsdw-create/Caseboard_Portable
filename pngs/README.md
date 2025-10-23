# Brand Assets for Caseboard Dashboard

This directory contains the McMath Woods P.A. brand assets used in the Caseboard application.

## Web Dashboard Assets

The web dashboard (`web/static/index.html`) references the following files:

- `McMathWoods_M_Brandmark_Copper.png` - Main brandmark for the header
- `McMathWoods_Seal_Copper.png` - Seal image for branding

## Current Files

The directory currently contains various versions of the brand assets in different color schemes:

- **brandmark/** - Logo marks in various colors (black, dark, light, white, secondary variants)
- **horizontal/** - Horizontal logo layouts
- **vertical/** - Vertical logo layouts

## Setup Instructions

To use the web dashboard with proper branding:

1. Rename or copy the appropriate copper-colored brandmark file to `McMathWoods_M_Brandmark_Copper.png`
2. Rename or copy the appropriate copper-colored seal file to `McMathWoods_Seal_Copper.png`

Alternatively, you can edit `web/static/index.html` to reference the existing filenames.

## Note

The web application accesses these files via a symlink at `web/static/pngs -> ../../pngs`.
