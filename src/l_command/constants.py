"""Constants for the l-command."""

# Size constants
JSON_CONTENT_CHECK_BYTES = 1024
MAX_JSON_SIZE_BYTES = 10 * 1024 * 1024  # 10MB limit for jq processing
MEDIUM_JSON_LINES_THRESHOLD = 100  # Lines threshold for using less with JSON files

# Timeout constants for external tools (in seconds)
# Quick utilities: fast operations like formatting/validation
TIMEOUT_QUICK = 30  # xmllint, yq, jq, file

# Processing tools: operations that analyze file content
TIMEOUT_PROCESSING = 60  # ffprobe, pdfminer operations, unzip/tar listing

# Rendering tools: operations that render or transform content
TIMEOUT_RENDERING = 45  # timg, glow, mdcat, pandoc, bat, hexdump
