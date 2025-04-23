# File sorting tool

A Windows utility that automatically organizes files into quarterly folders based on their modification dates.

## Core Features

- Organizes files into quarterly folders (Q1-2025, Q2-2025, etc.)
- Moves files older than 90 days
- Preserves newer files in the root directory
- Uses multi-threading for efficient processing
- Can handle large numbers of files. Tests for releases are done on ~10000 files.

## Safety Features

- Requires user confirmation before any operation
- Automatically skips locked or in-use files
- Maintains detailed operation logs
- Skips system files (.exe and .log)
- Checks for existing files at destination

## Usage

1. Run the executable in the directory you want to organize
   1. you can specify default directory in source code
   2. user is able to start application with startup parameter `--path "C:\your\target\location"`
2. Review and confirm the operation
3. Monitor progress through console output
4. Check logs for detailed operation history

## Example Output Structure

```
Before:
/your-directory/
    old_report_2024.pdf      # Old file (will be moved)
    quarterly_data.xlsx      # Old file (will be moved)
    recent_changes.docx      # Recent file (stays)
    meeting_notes.txt        # Recent file (stays)
    important_draft.doc      # Currently in use (will be skipped)

After:
/your-directory/
    Q1-2025/
        old_report_2024.pdf
    Q2-2025/
        quarterly_data.xlsx
    recent_changes.docx      # Stays (less than 90 days old)
    meeting_notes.txt        # Stays (less than 90 days old)
    important_draft.doc      # Stays (was in use)
    file_organizer.log
    file_organizer.exe
```

## Technical Details

- Written in Python
- Windows compatible
- No installation required
- Runs from executable
- Creates logs in working directory

## Future improvements in TODO
- Prohibit essential OS directories
- Linux support
- Improve logging
