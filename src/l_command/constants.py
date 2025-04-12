"""Constants for the l-command."""

# Size constants
JSON_CONTENT_CHECK_BYTES = 1024
MAX_JSON_SIZE_BYTES = 10 * 1024 * 1024  # 10MB limit for jq processing
MEDIUM_JSON_LINES_THRESHOLD = 100  # Lines threshold for using less with JSON files
