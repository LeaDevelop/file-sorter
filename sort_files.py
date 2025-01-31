# Copyright (c) 2025 Lea 'LeaDevelop' N.
# Licensed under BSD 3-Clause License - see LICENSE file for details

from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import os
import logging
import psutil
import argparse
import signal

CURRENT_RELEVANT_TIME_FRAME = 90
MAX_WORKERS = max(1, psutil.cpu_count(logical=True))
FILE_SORTER_LOG = "file_sorter.log"
DEFAULT_PATH_TO_SORT = r"C:\test\default-target"

# Global shutdown event
shutdown_event = Event()


def get_user_confirmation(target_path):
    """
    Ask user for confirmation before proceeding with file sorting.
    Parameters: target_path (str): The directory path where files will be sorted
    Returns True if user confirms, else False.
    """
    print("\nFile sorting tool")
    print("=====================")
    print("\nYou can specify a different directory using --path parameter")
    print(f"Default directory: {DEFAULT_PATH_TO_SORT}")
    print(f"\nCurrent selected target directory for file sorting: 🎯 {target_path}")
    print("\nThis tool will:")
    print("1. Scan all files in the target directory")
    print(f"2. Move files older than {CURRENT_RELEVANT_TIME_FRAME} days into quarter-based folders (Q1-YEAR, Q2-YEAR, etc.)")
    print(f"3. Skip locked files and maintain a detailed log - {FILE_SORTER_LOG}")
    print("\nAre you sure you want to proceed? (y/n): ", end='')

    try:
        response = input().lower().strip()
        return response == 'y' or response == 'yes'
    except (KeyboardInterrupt, EOFError):
        logging.info("User interrupted the confirmation prompt")
        return False


def should_move_file(modification_date):
    """
    Determine if file should be moved based on last modified date.
    Returns True if file is older than CURRENT_RELEVANT_TIME_FRAME days.
    """
    cutoff_date = datetime.now() - timedelta(days=CURRENT_RELEVANT_TIME_FRAME)
    return modification_date < cutoff_date


def signal_handler(*_):
    """Handle shutdown signals gracefully"""
    print("\nShutdown signal received. Cleaning up...")
    logging.info("Shutdown signal received. Waiting for ongoing operations to complete...")
    shutdown_event.set()


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Set up argument parser
parser = argparse.ArgumentParser()
parser.add_argument('--path', help='Target directory path (overrides default path)')

# Parse arguments, use default if no path provided
args = parser.parse_args()
DIRECTORY_PATH = args.path if args.path else DEFAULT_PATH_TO_SORT

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


def move_file(file_path):
    """Move file to appropriate quarter directory based on last modified date."""
    # Check if shutdown was requested
    if shutdown_event.is_set():
        return

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

        # Check for shutdown again before file operations
        if shutdown_event.is_set():
            return

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

        # Use ThreadPoolExecutor with all available logical processors
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(move_file, file_path) for file_path in file_paths]

            # Wait for all tasks to complete or shutdown
            for future in futures:
                if not shutdown_event.is_set():
                    future.result()  # This will raise any exceptions that occurred

        if shutdown_event.is_set():
            logging.info("Graceful shutdown completed")
        else:
            logging.info("File sorting completed successfully")

    except Exception as e:
        logging.error(f"Error during file sorting: {str(e)}")
    finally:
        logging.info("Cleanup completed")


if __name__ == "__main__":
    try:
        if get_user_confirmation(DIRECTORY_PATH):
            logging.info("Starting File sorting tool")
            logging.info(f"User confirmed. Starting file sorting in: {DIRECTORY_PATH}")
            sort_files(DIRECTORY_PATH)
            if not shutdown_event.is_set():
                print(f"\n\nFile sorting completed. Check {FILE_SORTER_LOG} for details.")
        else:
            logging.info("User cancelled operation")
            print("\nOperation cancelled by user.")
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt")
    finally:
        logging.info("Program terminated")
        input("🏁 Press Enter to exit...")
