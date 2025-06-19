#!/bin/bash

# --- Get the directory where the script is located ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# --- Define paths relative to the script's location ---
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"
LOCAL_FILE="$PROJECT_ROOT/lineage/wordpress_urls.csv"
# A temporary file to hold the latest version from the server
TEMP_FILE="$PROJECT_ROOT/lineage/remote_latest.tmp"

# --- Load configuration from the .env file at the project root ---
if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

# Check if the variables are loaded
if [ -z "$REMOTE_USER" ] || [ -z "$REMOTE_HOST" ] || [ -z "$REMOTE_PATH" ]; then
    echo "Error: REMOTE_USER, REMOTE_HOST, and REMOTE_PATH must be set in your .env file."
    echo "Searched for .env file at: $ENV_FILE"
    exit 1
fi

echo "Checking remote file status on $REMOTE_HOST..."

# First, check if the remote file even exists before we do anything
if ! ssh $REMOTE_USER@$REMOTE_HOST "[ -f $REMOTE_PATH ]"; then
    echo "Error: Remote file not found at $REMOTE_PATH"
    exit 1
fi

# --- Main Logic ---

# Check if the LOCAL file exists
if [ -f "$LOCAL_FILE" ]; then
    # LOCAL FILE EXISTS: This is an update run.
    echo "Local file found. Checking for new URLs..."

    # 1. Download the latest version of the remote file to a temporary location
    if ! ssh $REMOTE_USER@$REMOTE_HOST "cat $REMOTE_PATH" > "$TEMP_FILE"; then
        echo "Error: Failed to download remote file for comparison."
        exit 1
    fi

    # 2. Compare the temp file (latest) with the local file to find lines that are NEW.
    NEW_ROWS=$(grep -v -x -f "$LOCAL_FILE" "$TEMP_FILE")

    # 3. Append the new URLs if any were found
    if [ -n "$NEW_ROWS" ]; then
        echo "New URLs found. Appending to local file..."
        # We add a newline just in case the local file doesn't end with one
        echo "" >> "$LOCAL_FILE"
        echo "$NEW_ROWS" >> "$LOCAL_FILE"
        echo "Update complete."
    else
        echo "Your local file is already up-to-date."
    fi

    # 4. Clean up the temporary file
    rm "$TEMP_FILE"

else
    # LOCAL FILE DOES NOT EXIST: This is the first run.
    echo "Local file not found. Performing initial download and creating header..."

    # 1. Create the local file and write the correct two-column header.
    echo "filename,url" > "$LOCAL_FILE"

    # 2. Append the content from the remote file to the new local file.
    #    Note the '>>' which means APPEND, not overwrite.
    if ssh $REMOTE_USER@$REMOTE_HOST "cat $REMOTE_PATH" >> "$LOCAL_FILE"; then
        echo "Initial download complete. File saved with header to: $LOCAL_FILE"
    else
        echo "Error: Failed to append remote content to local file."
        # Clean up the partial file if the download fails
        rm "$LOCAL_FILE"
        exit 1
    fi
fi

echo "Done."