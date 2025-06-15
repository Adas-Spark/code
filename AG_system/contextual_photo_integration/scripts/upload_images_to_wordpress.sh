#!/bin/bash

# Define paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"
LOCAL_IMAGE_DIR="${PROJECT_ROOT}/processed_webp/"

# Load configuration from .env file
if [ -f "$ENV_FILE" ]; then
  export $(grep -v '^#' "$ENV_FILE" | xargs)
else
  echo "Error: .env file not found at ${ENV_FILE}"
  exit 1
fi

# Check for required variables
if [ -z "$REMOTE_USER" ] || [ -z "$REMOTE_HOST" ] || [ -z "$REMOTE_SITE_PATH" ]; then
  echo "Error: Required variables (REMOTE_USER, REMOTE_HOST, REMOTE_SITE_PATH) are not set in ${ENV_FILE}"
  exit 1
fi

# User confirmation
read -p "This script will attempt to upload images to WordPress. Continue? (y/n): " confirm
if [[ "$confirm" != [yY] && "$confirm" != [yY][eE][sS] ]]; then
  echo "Upload cancelled by user."
  exit 0
fi

# Fetch existing media filenames from WordPress
echo "Fetching list of existing media from WordPress..."
# Using --porcelain with post list to potentially simplify output, though it's typically for create/update.
# Sticking to CSV for now as it's reliable for lists.
REMOTE_MEDIA_CSV=$(wp post list --post_type=attachment --fields=post_name --format=csv --ssh="${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_SITE_PATH}" 2>&1)
WP_CLI_EXIT_CODE=$?

if [ $WP_CLI_EXIT_CODE -ne 0 ]; then
  echo "Error fetching media list from WordPress (Exit Code: $WP_CLI_EXIT_CODE):"
  echo "$REMOTE_MEDIA_CSV" # Output WP-CLI error
  exit 1
fi

# Store remote post_names in an array, skipping the header
mapfile -t REMOTE_POST_NAMES < <(echo "$REMOTE_MEDIA_CSV" | tail -n +2 | sed 's/"//g') # Remove quotes if any

if [ ${#REMOTE_POST_NAMES[@]} -eq 0 ] && [[ "$REMOTE_MEDIA_CSV" == *"post_name"* ]]; then
  # If the output contained the header "post_name" but array is empty, means no media.
  echo "No existing media found on remote."
elif [ ${#REMOTE_POST_NAMES[@]} -eq 0 ]; then
    # If array is empty and no header, might be an issue with parsing or actual empty list.
    echo "No existing media found on remote or potential error parsing list. CSV output was:"
    echo "$REMOTE_MEDIA_CSV"
fi

echo "Found ${#REMOTE_POST_NAMES[@]} existing media items on remote."

# Check if local image directory is empty
if ! ls "${LOCAL_IMAGE_DIR}"*.webp 1> /dev/null 2>&1; then
  echo "No .webp images found in ${LOCAL_IMAGE_DIR}"
  exit 0
fi

echo "Starting image upload process..."
# Loop through images and attempt to import
for image_path in "${LOCAL_IMAGE_DIR}"*.webp; do
  if [ -f "$image_path" ]; then
    filename=$(basename "$image_path")
    local_post_name_stem="${filename%.*}"

    title=$(echo "$local_post_name_stem" | sed -e 's/-/ /g' -e 's/\b\(.\)/\u\1/g')
    wp_post_name="$local_post_name_stem"

    found=0
    for remote_name in "${REMOTE_POST_NAMES[@]}"; do
      if [[ "$remote_name" == "$wp_post_name" ]]; then
        found=1
        break
      fi
    done

    if [ "$found" -eq 1 ]; then
      echo "Skipping (already exists on remote): ${filename} (post_name: ${wp_post_name})"
    else
      echo "Attempting to upload: ${filename}"
      # Attempt to use --porcelain to get just the ID on success
      import_output=$(wp media import "${image_path}" --ssh="${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_SITE_PATH}" --title="${title}" --post_name="${wp_post_name}" --porcelain 2>&1)
      import_exit_code=$?

      if [ $import_exit_code -eq 0 ]; then
        # Check if output is a number (attachment ID)
        if [[ "$import_output" =~ ^[0-9]+$ ]]; then
          echo "Success: Imported '${filename}' as attachment ID ${import_output}."
        else
          # Sometimes --porcelain might give other success messages if not an ID
          echo "Success: Imported '${filename}'. WP-CLI output: ${import_output}"
        fi
      else
        echo "Error importing '${filename}' (Exit Code: $import_exit_code):"
        echo "Output: ${import_output}"
      fi
    fi
  fi
done

echo "Image upload process completed."
exit 0
