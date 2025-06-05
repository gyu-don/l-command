# L command

`l` command is a smart file and directory viewer that can replace both `less` and `ls`. It intelligently detects the content type and displays it in the most appropriate way.

## Usage

- `l /path/to/file`: Display file content appropriately
  - **PDF files**: Extract and display text content using `pdfminer.six`
  - **Image files**: Display in terminal using `timg` or show metadata
  - **Audio/Video files**: Show detailed metadata using `ffprobe`
  - **XML/HTML files**: Format and validate using `xmllint`
  - **CSV/TSV files**: Display structured table with column information
  - **Markdown files**: Render using `glow`, `mdcat`, or `pandoc`
  - **YAML files**: Format and validate using `yq` with color output
  - **JSON files**: Format and display using `jq`
  - **Archive files**: List contents using appropriate tools (`unzip -l`, `tar -tvf`)
  - **Binary files**: Display using `hexdump -C`
  - **Text files**: Short files via `cat`, long files via `less -RFX`
- `l /path/to/directory`: Works as `ls -la --color=auto /path/to/directory`

## Detailed Behavior

### File Type Detection and Processing

The tool uses a priority-based handler system to process different file types:

**Priority Order**: Image (65) > PDF (60) > Media (55) > JSON (50) > XML/HTML (45) > CSV (40) > Markdown (35) > YAML (30) > Archive (80) > Binary (20) > Default (0)

#### PDF Files (Priority: 60)
- **Extensions**: `.pdf`
- **Content Detection**: Files starting with `%PDF-`
- **Processing**: Extract text using `pdfminer.six`, display metadata and content
- **Fallback**: Show file information when `pdfminer.six` is unavailable

#### Image Files (Priority: 65)
- **Extensions**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.webp`, `.tiff`, `.tif`
- **Content Detection**: Magic bytes for PNG, JPEG, GIF, BMP, WebP, TIFF
- **Processing**: Display in terminal using `timg`, show dimensions and metadata
- **Fallback**: Show file information and dimensions when `timg` is unavailable

#### Audio/Video Files (Priority: 55)
- **Extensions**: Audio (`.mp3`, `.flac`, `.wav`, `.aac`, `.ogg`, `.m4a`, `.wma`), Video (`.mp4`, `.mkv`, `.avi`, `.mov`, `.wmv`, `.flv`, `.webm`, `.m4v`, `.3gp`)
- **Processing**: Analyze using `ffprobe` to show format, duration, bitrate, streams, and metadata
- **Fallback**: Show basic file information when `ffmpeg` is unavailable

#### XML/HTML Files (Priority: 45)
- **Extensions**: `.xml`, `.html`, `.htm`, `.xhtml`, `.svg`, `.xsl`, `.xslt`
- **Content Detection**: XML declaration, DOCTYPE, or XML/HTML tag patterns
- **Processing**: Format using `xmllint --format`, validate syntax
- **Fallback**: Show raw content when `xmllint` is unavailable

#### CSV/TSV Files (Priority: 40)
- **Extensions**: `.csv`, `.tsv`, `.txt` (with CSV content detection)
- **Content Detection**: Consistent delimiter patterns across lines
- **Processing**: Display structured table with column headers and data preview
- **Features**: Auto-detect delimiters (comma, tab, semicolon, pipe), show row/column counts

#### Markdown Files (Priority: 35)
- **Extensions**: `.md`, `.markdown`, `.mdown`, `.mkd`, `.mdx`
- **Processing**: Render using `glow` (with smart paging), `mdcat`, or `pandoc`
- **Features**: Smart paging based on content length, syntax highlighting fallback with `bat`
- **Fallback**: Show source with syntax highlighting

#### YAML Files (Priority: 30)
- **Extensions**: `.yaml`, `.yml`
- **Content Detection**: YAML document markers (`---`, `%YAML`) or YAML structure patterns
- **Processing**: Format using `yq --colors`, validate syntax
- **Fallback**: Show raw content with syntax highlighting when `yq` is unavailable

#### JSON Files (Priority: 50)
- **Extensions**: `.json`
- **Content Detection**: Files starting with `{` or `[` (UTF-8 encoded)
- **Processing**: Format using `jq --color-output`, validate syntax
- **Features**: Size limit check (10MB), smart paging
- **Fallback**: Show raw content for invalid JSON or when `jq` is unavailable

#### Archive Files (Priority: 80)
- **Extensions**: ZIP (`.zip`, `.jar`, `.war`, `.ear`, `.apk`, `.ipa`), TAR (`.tar.gz`, `.tgz`, `.tar.bz2`, `.tbz2`, `.tar.xz`, `.txz`, `.tar.zst`)
- **Processing**: List contents using `unzip -l` or `tar -tvf`
- **Features**: Smart paging for large archive listings

#### Binary Files (Priority: 20)
- **Detection**: Uses `file` command or content-based detection (null bytes, non-printable characters)
- **Processing**: Display using `hexdump -C`
- **Features**: Handles various binary formats

#### Text Files (Default Priority: 0)
- **Processing**: Automatically detects file size and line count
- **Features**: Uses `cat` for short files, `less -RFX` for long files
- **Smart Paging**: Compares file line count with terminal height

## Options

Currently, the command line arguments are as follows:

- Positional argument `path`: Path to the file or directory to display (default: current directory `.`)

## Use Cases

- **View file content quickly**: `l file.txt`
- **Check directory contents**: `l ./myfolder`
- **Read PDF documents**: `l document.pdf`
- **View images in terminal**: `l image.png`
- **Analyze media files**: `l video.mp4` or `l audio.mp3`
- **Format structured data**: `l data.json`, `l config.yaml`, `l data.csv`
- **Read documentation**: `l README.md`
- **Validate markup**: `l page.html`, `l config.xml`
- **Inspect archives**: `l archive.zip`, `l backup.tar.gz`
- **Debug binary files**: `l binary.bin`

## Optional Dependencies

For enhanced functionality, install these optional tools:

- **PDF support**: `pip install pdfminer.six`
- **Image display**: Install `timg` via your package manager
- **Media analysis**: Install `ffmpeg` (includes `ffprobe`)
- **XML formatting**: Install `libxml2-utils` (includes `xmllint`)
- **Markdown rendering**: Install `glow`, `mdcat`, or `pandoc`
- **YAML processing**: Install `yq`
- **Syntax highlighting**: Install `bat` for enhanced fallback display

The tool gracefully handles missing dependencies by showing basic file information and falling back to appropriate display methods.
