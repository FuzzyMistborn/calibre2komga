# calibre2komga, a Calibre to Komga Migration Script

While I like Calibre (and still plan to use it for ingesting books), I grew dissatisfied with Calibre-Web (and Calibre-Web-Automated).  I liked Komga and wanted to switch, but didn't want to spend time painfully migrating my library to the structure Komga likes.  So I asked my buddy Claude(.ai) to help me write a migration script.  After some back and forth and tweaks, this is the result.  So yes, it's 100% AI coded, but 1) it's non-desctructive to your Calibre library and 2) it's at least been tested by me a bit.  That being said, if you see something/run into issues, by all means raise an issue and we'll work on it.

A Python script that migrates ebooks from [Calibre's](https://github.com/kovidgoyal/calibre) folder structure to [Komga's](https://github.com/gotson/komga) expected format, making it easy to transition your ebook library to Komga's comic/ebook server.

## Overview

This script reads Calibre's metadata database to accurately organize books by series and converts the folder structure from Calibre's `Author/Title/files` format to Komga's flat `Series/files` format.

### Before (Calibre Structure)
```
📁 Calibre Library/
├── 📁 Brandon Sanderson/
│   ├── 📁 The Way of Kings (45)/
│   │   └── 📄 The Way of Kings.epub
│   ├── 📁 Words of Radiance (22)/
│   │   └── 📄 Words of Radiance.epub
│   └── 📁 Warbreaker (178)/
│       └── 📄 Warbreaker.epub
```

### After (Komga Structure)
```
📁 Komga Library/
├── 📁 Brandon Sanderson - The Stormlight Archive/
│   ├── 📄 Volume 01 - The Way of Kings.epub
│   └── 📄 Volume 02 - Words of Radiance.epub
└── 📁 Brandon Sanderson/
    └── 📄 Warbreaker.epub
```

## Features

- ✅ **Database-driven**: Uses Calibre's SQLite database for accurate series detection
- ✅ **Series organization**: Groups books properly using Calibre's series metadata
- ✅ **Volume numbering**: Maintains correct order using series index from Calibre
- ✅ **Title cleaning**: Removes Calibre's auto-generated numbering suffixes (e.g., "(84)")
- ✅ **Format filtering**: Only migrates `.epub` and `.kepub` files
- ✅ **Dry run mode**: Preview changes before migration
- ✅ **Author filtering**: Migrate specific authors only
- ✅ **Cross-platform**: Works on Windows, macOS, and Linux
- ✅ **Safe migration**: Preserves original files, copies to new location

## Requirements

- Python 3.6 or higher
- Access to a Calibre library folder
- Destination folder for Komga library

## Installation

1. Download the `migrate.py` script
2. Ensure Python 3.6+ is installed on your system
3. No additional dependencies required (uses Python standard library only)

## Usage

### Basic Migration
```bash
python migrate.py /path/to/calibre/library /path/to/komga/library
```

### Dry Run (Recommended First)
Preview what will be migrated without making any changes:
```bash
python migrate.py /path/to/calibre/library /path/to/komga/library --dry-run
```

### Migrate Specific Author
```bash
python migrate.py /path/to/calibre/library /path/to/komga/library --author "Brandon Sanderson"
```

### Verbose Output
```bash
python migrate.py /path/to/calibre/library /path/to/komga/library --verbose
```

### Combined Options
```bash
python migrate.py /path/to/calibre/library /path/to/komga/library --dry-run --author "Isaac Asimov" --verbose
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `calibre_path` | Path to your Calibre library directory (required) |
| `komga_path` | Path to your Komga library directory (required, will be created if doesn't exist) |
| `--dry-run` | Show what would be migrated without copying files |
| `--author "Name"` | Filter migration to specific author (case insensitive partial match) |
| `--verbose` | Enable detailed logging output |

## How It Works

1. **Reads Calibre Database**: Connects to `metadata.db` to extract book metadata, series information, and series indices
2. **Series Detection**: Uses Calibre's series metadata for accurate grouping, falls back to title pattern matching for standalone books
3. **Folder Structure**: Creates series folders and places files directly inside (no subfolders)
4. **File Naming**: Renames files to include volume information for series books
5. **Format Filtering**: Only processes `.epub` and `.kepub` files

## File Organization Logic

### For Books in a Series
- **Folder**: `Author - Series Name`
- **Files**: `Volume XX - Book Title.epub`

Example: `Brandon Sanderson - Mistborn/Volume 01 - The Final Empire.epub`

### For Standalone Books
- **Folder**: `Author Name`
- **Files**: `Book Title.epub`

Example: `Brandon Sanderson/Warbreaker.epub`

## Migration Statistics

The script provides detailed statistics after completion:
```
Migration Summary:
  Total books found: 1,247
  Books migrated: 1,198
  Books skipped: 45
  Errors: 4
  Success rate: 96.1%
```

## Important Notes

- **Backup First**: Always backup your libraries before migration
- **Non-destructive**: Original Calibre library remains unchanged
- **File Conflicts**: Existing files in destination are skipped with warnings
- **Series Only**: Books without `.epub` or `.kepub` formats are skipped
- **Metadata**: Only ebook files are copied; metadata and cover files are excluded

## Troubleshooting

### "No metadata.db found" Error
- Ensure you're pointing to the root Calibre library folder
- The folder should contain a `metadata.db` file

### "No supported ebook files found" Warning
- Book only has formats other than `.epub` or `.kepub`
- Consider converting books in Calibre first if needed

### File Permission Errors
- Ensure you have read access to Calibre library
- Ensure you have write access to destination folder

## Related Projects

- [Calibre](https://github.com/kovidgoyal/calibre) - E-book management software
- [Komga](https://github.com/gotson/komga) - Media server for comics/ebooks

---

**Disclaimer**: This script is not officially affiliated with Calibre or Komga projects. Use at your own risk and always backup your data before migration.
