# L command

`l` command is a smart file and directory viewer that can replace both `less` and `ls`. It intelligently detects the content type and displays it in the most appropriate way.

## Usage

- `l /path/to/file`: Display file content appropriately
  - Short files: Display using `cat`
  - Long files: Display using `less -RFX`
  - JSON files: Format and display using `jq`
  - Archive files: List contents using appropriate tools (`unzip -l`, `tar -tvf`)
  - Binary files: Display using `hexdump -C`
- `l /path/to/directory`: Works as `ls -la --color=auto /path/to/directory`
- `l /path/to/json`: Detects JSON files and formats them using `jq`
- `l /path/to/archive`: Detects archive files (zip, tar, etc.) and lists their contents

## Detailed Behavior

- Automatically detects file size and line count, using `cat` for short files and `less` for long files
- Detects terminal height and uses `less` if the file has more lines than the terminal height
- Automatic JSON detection and formatting:
  - Files with `.json` extension
  - Files without extension but starting with `{` or `[` (UTF-8 encoded)
  - Performs syntax check using `jq empty`, falling back to default display for invalid JSON
  - Falls back to default display for large JSON files (>10MB)
- Archive file detection and content listing:
  - ZIP files (including .jar, .war, .ear, .apk, .ipa)
  - TAR archives (including .tar.gz, .tgz, .tar.bz2, .tbz2, .tar.xz, .txz, .tar.zst)
- Binary file detection and hexdump display:
  - Uses `file` command to detect binary files when available
  - Falls back to content-based detection (checking for null bytes and non-printable characters)
  - Displays binary files using `hexdump -C`
- Directory detection and listing

## Options

Currently, the command line arguments are as follows:

- Positional argument `path`: Path to the file or directory to display (default: current directory `.`)

## Use Cases

- View file content quickly: `l file.txt`
- Check directory contents at a glance: `l ./myfolder`
- Format and read JSON files: `l data.json`
- List contents of archive files: `l archive.zip`
- View binary files in hexdump format: `l binary.bin`
