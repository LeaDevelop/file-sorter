# Copyright (c) 2025 Lea 'LeaDevelop' N.
# Licensed under BSD 3-Clause License - see LICENSE file for details

import os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import logging
import psutil
import sys
import argparse

CURRENT_RELEVANT_TIME_FRAME = 90
MAX_WORKERS = max(1, psutil.cpu_count(logical=True))
FILE_SORTER_LOG = "file_sorter.log"
DEFAULT_PATH_TO_SORT = r"C:\test\default-target"

# Determine run mode and set directory
if getattr(sys, 'frozen', False):
    # Running as exe
    DIRECTORY_PATH = os.path.dirname(sys.executable)
else:
    # Running as script - require path
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', required=True, help='Target directory path')
    DIRECTORY_PATH = parser.parse_args().path

# Set up logging
log_file = os.path.join(DIRECTORY_PATH, FILE_SORTER_LOG)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)


def get_user_confirmation(directory):
    """
    Ask user for confirmation before proceeding with file sorting.
    Returns True if user confirms, else False.
    """
    print("\nFile sorting tool")
    print("=====================")
    print(f"\nTarget Directory: {directory}")
    print("\nThis tool will:")
    print("1. Scan all files in the directory")
    print(f"2. Move files older than {CURRENT_RELEVANT_TIME_FRAME} days into quarter-based folders (Q1-YEAR, Q2-YEAR, etc.)")
    print(f"3. Skip locked files and maintain a detailed log - {FILE_SORTER_LOG}")
    print("\nAre you sure you want to proceed? (y/n): ", end='')

    try:
        response = input().lower().strip()
        return response == 'y' or response == 'yes'
    except Exception as e:
        logging.error(f"Error getting user input: {str(e)}")
        return False


def should_move_file(modification_date):
    """
    Determine if file should be moved based on last modified date.
    Returns True if file is older than CURRENT_RELEVANT_TIME_FRAME days.
    """
    cutoff_date = datetime.now() - timedelta(days=CURRENT_RELEVANT_TIME_FRAME)
    return modification_date < cutoff_date


def move_file(file_path):
    """Move file to appropriate quarter directory based on last modified date."""
    try:
        # Skip directories and special files
        if not os.path.isfile(file_path):
            return

        # Skip log files
        if file_path.endswith('.log'):
            logging.debug(f"Skipping log file: {file_path}")
            return

        # Skip the exe itself
        if file_path.endswith('.exe'):
            return

        modified_time = os.path.getmtime(file_path)
        modified_date = datetime.fromtimestamp(modified_time)

        # Skip files newer than CURRENT_RELEVANT_TIME_FRAME days
        if not should_move_file(modified_date):
            logging.info(f"Skipping {file_path} - within {CURRENT_RELEVANT_TIME_FRAME}-day retention period")
            return

        quarter = (modified_date.month - 1) // 3 + 1
        year = modified_date.year
        quarter_dir = f"Q{quarter}-{year}"
        quarter_path = os.path.join(os.path.dirname(file_path), quarter_dir)

        # Create quarter directory when it doesn't exist
        if not os.path.exists(quarter_path):
            os.makedirs(quarter_path, exist_ok=True)

        dest_path = os.path.join(quarter_path, os.path.basename(file_path))

        # Verify if destination file already exists
        if os.path.exists(dest_path):
            logging.warning(f"File already exists at destination: {dest_path}")
            return

        # Attempt to move the file
        os.rename(file_path, dest_path)
        logging.info(f"Successfully moved {file_path} to {dest_path}")

    except OSError as e:
        if e.errno == 13:
            logging.warning(f"File {file_path} is locked or permission denied. Skipping.")
        else:
            logging.error(f"Error processing {file_path}: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error processing {file_path}: {str(e)}")


def sort_files(dir_path):
    """Sort files into quarter directories using thread pool."""
    try:
        # Verify if directory exists
        if not os.path.exists(dir_path):
            logging.error(f"Directory {dir_path} does not exist")
            return

        # Get list of files (not directories) in the specified path
        file_paths = [
            os.path.join(dir_path, filename)
            for filename in os.listdir(dir_path)
            if os.path.isfile(os.path.join(dir_path, filename))
        ]

        logging.info(f"Found {len(file_paths)} files to process")
        logging.info(f"Using {MAX_WORKERS} worker threads")

        # Use ThreadPoolExecutor with half of available logical processors
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(move_file, file_paths)

        logging.info("File organization completed")

    except Exception as e:
        logging.error(f"Error during file organization: {str(e)}")


if __name__ == "__main__":
    logging.info("Starting File sorting tool")

    # Get user confirmation before proceeding
    if get_user_confirmation(DIRECTORY_PATH):
        logging.info(f"User confirmed. Starting file organization in: {DIRECTORY_PATH}")
        sort_files(DIRECTORY_PATH)
        print(f"\nFile sorting completed. Check {FILE_SORTER_LOG} for details.")
    else:
        logging.info("User cancelled operation")
        print("\nOperation cancelled by user.")

    # Keep console window open
    input("\nPress Enter to exit...")
