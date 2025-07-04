#!/usr/bin/env python3
"""
Calibre to Komga Migration Script

This script migrates ebooks from Calibre's folder structure to Komga's expected format.
Calibre uses: Author/Title/book_files
Komga expects: Series/files (where files are directly in series folder, not subfolders)

Requirements:
- Python 3.6+
- Access to Calibre library folder
- Destination folder for Komga library
"""

import os
import shutil
import argparse
import logging
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CalibreKomgaMigrator:
    def __init__(self, calibre_path: str, komga_path: str, dry_run: bool = False):
        self.calibre_path = Path(calibre_path)
        self.komga_path = Path(komga_path)
        self.dry_run = dry_run
        
        # Supported ebook formats - only epub and kepub
        self.supported_formats = {'.epub', '.kepub'}
        
        # Statistics
        self.stats = {
            'total_books': 0,
            'migrated_books': 0,
            'skipped_books': 0,
            'errors': 0
        }
        
        # Calibre metadata database connection
        self.metadata_db_path = self.calibre_path / 'metadata.db'
        self.metadata_cache = {}
    
    def validate_paths(self) -> bool:
        """Validate that the source and destination paths exist and are accessible."""
        if not self.calibre_path.exists():
            logger.error(f"Calibre library path does not exist: {self.calibre_path}")
            return False
        
        if not self.calibre_path.is_dir():
            logger.error(f"Calibre library path is not a directory: {self.calibre_path}")
            return False
            
        # Check for Calibre metadata.db file
        if not self.metadata_db_path.exists():
            logger.error(f"No metadata.db found in {self.calibre_path}. This doesn't appear to be a Calibre library.")
            return False
        
        # Create Komga path if it doesn't exist
        if not self.dry_run:
            self.komga_path.mkdir(parents=True, exist_ok=True)
        
        return True
    
    def load_calibre_metadata(self) -> bool:
        """Load metadata from Calibre database."""
        try:
            conn = sqlite3.connect(self.metadata_db_path)
            cursor = conn.cursor()
            
            # Query to get book metadata including series information
            query = """
            SELECT 
                b.id,
                b.title,
                b.path,
                b.series_index,
                a.name as author_name,
                s.name as series_name,
                GROUP_CONCAT(d.name, ',') as formats
            FROM books b
            LEFT JOIN books_authors_link bal ON b.id = bal.book
            LEFT JOIN authors a ON bal.author = a.id
            LEFT JOIN books_series_link bsl ON b.id = bsl.book
            LEFT JOIN series s ON bsl.series = s.id
            LEFT JOIN data d ON b.id = d.book
            GROUP BY b.id
            ORDER BY a.name, s.name, b.series_index, b.title
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            for row in results:
                book_id, title, path, series_index, author_name, series_name, formats = row
                
                # Handle multiple authors (take the first one for simplicity)
                if author_name:
                    author_name = author_name.split(',')[0].strip()
                
                self.metadata_cache[path] = {
                    'id': book_id,
                    'title': title,
                    'author': author_name or 'Unknown Author',
                    'series': series_name,
                    'series_index': series_index,
                    'formats': formats.split(',') if formats else []
                }
            
            conn.close()
            logger.info(f"Loaded metadata for {len(self.metadata_cache)} books from Calibre database")
            return True
            
        except Exception as e:
            logger.error(f"Error loading Calibre metadata: {str(e)}")
            return False
    
    def get_book_metadata(self, book_path: Path) -> Optional[Dict]:
        """Get metadata for a specific book from the cache."""
        # Convert absolute path to relative path from calibre library
        try:
            relative_path = book_path.relative_to(self.calibre_path)
            path_key = str(relative_path).replace('\\', '/')
            return self.metadata_cache.get(path_key)
        except ValueError:
            # Path is not relative to calibre_path
            return None
    
    def clean_calibre_title(self, title: str) -> str:
        """Remove Calibre's automatically generated numbering suffixes from titles."""
        if not title:
            return title
        
        # Remove patterns like " (84)", " (123)", etc. at the end of titles
        # This matches parentheses with only numbers inside at the end of the string
        cleaned = re.sub(r'\s*\(\d+\)\s*$', '', title)
        
        # Also handle cases with multiple spaces before parentheses
        cleaned = re.sub(r'\s+\(\d+\)\s*$', '', cleaned)
        
        return cleaned.strip()
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for cross-platform compatibility."""
        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip('. ')
        # Limit length to reasonable size
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        return sanitized
    
    def get_series_folder_name(self, metadata: Dict) -> str:
        """Generate series folder name from metadata."""
        author = metadata.get('author', 'Unknown Author')
        series = metadata.get('series')
        
        if series:
            # Use actual series name from Calibre
            return self.sanitize_filename(f"{author} - {series}")
        else:
            # For standalone books, use author as series name
            return self.sanitize_filename(f"{author}")
    
    def get_file_name(self, metadata: Dict, original_filename: str) -> str:
        """Generate the filename for the book file."""
        title = metadata.get('title', 'Unknown Title')
        series_index = metadata.get('series_index')
        series = metadata.get('series')
        
        # Clean the title of Calibre's auto-generated numbering
        clean_title = self.clean_calibre_title(title)
        
        # Get the original file extension
        original_path = Path(original_filename)
        extension = original_path.suffix
        
        if series and series_index:
            # For books in a series, use "Volume XX - Title" format
            if series_index == int(series_index):
                # Whole number
                volume_num = str(int(series_index)).zfill(2)
            else:
                # Decimal number
                volume_num = f"{series_index:05.1f}".replace('.', '_')
            filename = f"Volume {volume_num} - {clean_title}"
        else:
            # For standalone books, just use the title
            filename = clean_title
        
        return self.sanitize_filename(filename) + extension
    
    def find_ebook_files(self, book_path: Path) -> List[Path]:
        """Find all ebook files in a book's directory."""
        files = []
        for file_path in book_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                files.append(file_path)
        return files
    
    def migrate_book(self, book_path: Path) -> bool:
        """Migrate a single book from Calibre to Komga structure."""
        # Get metadata from Calibre database
        metadata = self.get_book_metadata(book_path)
        if not metadata:
            logger.warning(f"No metadata found for {book_path}, skipping")
            self.stats['skipped_books'] += 1
            return False
        
        author_name = metadata['author']
        book_title = metadata['title']
        
        # Find ebook files
        ebook_files = self.find_ebook_files(book_path)
        if not ebook_files:
            logger.warning(f"No supported ebook files found in {book_path}")
            self.stats['skipped_books'] += 1
            return False
        
        # Generate series folder name
        series_folder = self.get_series_folder_name(metadata)
        series_path = self.komga_path / series_folder
        
        # Show series info if available
        series_info = ""
        if metadata.get('series'):
            series_info = f" (Series: {metadata['series']}"
            if metadata.get('series_index'):
                series_info += f", Index: {metadata['series_index']}"
            series_info += ")"
        
        logger.info(f"Migrating: {author_name}/{book_title}{series_info} -> {series_folder}/")
        
        if not self.dry_run:
            try:
                # Create series directory
                series_path.mkdir(parents=True, exist_ok=True)
                
                # Copy ebook files directly to series folder
                for ebook_file in ebook_files:
                    # Generate new filename
                    new_filename = self.get_file_name(metadata, ebook_file.name)
                    dest_file = series_path / new_filename
                    
                    if dest_file.exists():
                        logger.warning(f"File already exists, skipping: {dest_file}")
                        continue
                    
                    shutil.copy2(ebook_file, dest_file)
                    logger.debug(f"Copied: {ebook_file} -> {dest_file}")
                
                self.stats['migrated_books'] += 1
                return True
                
            except Exception as e:
                logger.error(f"Error migrating {book_path}: {str(e)}")
                self.stats['errors'] += 1
                return False
        else:
            # Show what files would be created
            for ebook_file in ebook_files:
                new_filename = self.get_file_name(metadata, ebook_file.name)
                logger.info(f"[DRY RUN] Would create: {series_path / new_filename}")
            self.stats['migrated_books'] += 1
            return True
    
    def migrate_library(self, author_filter: Optional[str] = None) -> None:
        """Migrate the entire Calibre library to Komga format."""
        logger.info(f"Starting migration from {self.calibre_path} to {self.komga_path}")
        logger.info(f"Dry run: {self.dry_run}")
        
        if not self.validate_paths():
            return
        
        # Load metadata from Calibre database
        if not self.load_calibre_metadata():
            logger.error("Failed to load Calibre metadata. Exiting.")
            return
        
        # Process books based on metadata
        for path_key, metadata in self.metadata_cache.items():
            book_path = self.calibre_path / path_key
            
            if not book_path.exists() or not book_path.is_dir():
                logger.warning(f"Book path does not exist: {book_path}")
                continue
            
            # Apply author filter if specified
            if author_filter and author_filter.lower() not in metadata['author'].lower():
                continue
            
            self.stats['total_books'] += 1
            self.migrate_book(book_path)
        
        self.print_summary()
    
    def print_summary(self) -> None:
        """Print migration summary."""
        logger.info("Migration Summary:")
        logger.info(f"  Total books found: {self.stats['total_books']}")
        logger.info(f"  Books migrated: {self.stats['migrated_books']}")
        logger.info(f"  Books skipped: {self.stats['skipped_books']}")
        logger.info(f"  Errors: {self.stats['errors']}")
        
        if self.stats['total_books'] > 0:
            success_rate = (self.stats['migrated_books'] / self.stats['total_books']) * 100
            logger.info(f"  Success rate: {success_rate:.1f}%")


def main():
    parser = argparse.ArgumentParser(
        description='Migrate ebooks from Calibre to Komga folder structure',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Basic migration
  python migrate.py /path/to/calibre/library /path/to/komga/library
  
  # Dry run to see what would be migrated
  python migrate.py /path/to/calibre/library /path/to/komga/library --dry-run
  
  # Migrate only specific author
  python migrate.py /path/to/calibre/library /path/to/komga/library --author "Isaac Asimov"
  
  # Enable debug logging
  python migrate.py /path/to/calibre/library /path/to/komga/library --verbose
        '''
    )
    
    parser.add_argument('calibre_path', help='Path to Calibre library directory')
    parser.add_argument('komga_path', help='Path to Komga library directory (will be created if not exists)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated without actually copying files')
    parser.add_argument('--author', help='Filter by author name (case insensitive partial match)')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    migrator = CalibreKomgaMigrator(
        calibre_path=args.calibre_path,
        komga_path=args.komga_path,
        dry_run=args.dry_run
    )
    
    migrator.migrate_library(author_filter=args.author)


if __name__ == '__main__':
    main()
