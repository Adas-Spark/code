#!/bin/bash

# Define paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)" # Assuming scripts is under AG_system/contextual_photo_integration/scripts
ENV_FILE="${PROJECT_ROOT}/AG_system/contextual_photo_integration/.env" # More specific path to .env
LOCAL_IMAGE_DIR="${PROJECT_ROOT}/AG_system/contextual_photo_integration/processed_webp/"

# Define paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)" # Assuming scripts is under AG_system/contextual_photo_integration/scripts
ENV_FILE="${PROJECT_ROOT}/AG_system/contextual_photo_integration/.env" # More specific path to .env
LOCAL_IMAGE_DIR="${PROJECT_ROOT}/AG_system/contextual_photo_integration/processed_webp/"
LOCAL_THUMBNAIL_DIR="${PROJECT_ROOT}/AG_system/contextual_photo_integration/processed_webp_thumbnails/"
LINEAGE_CSV_PATH="${PROJECT_ROOT}/lineage/complete_image_lineage.csv" # Note: This might be FINAL_MASTER_DATA.csv based on previous tasks

# Load configuration from .env file (primarily for WP-CLI check, which is now replaced)
# Keep this structure if other parts of script might use .env vars in future
if [ -f "$ENV_FILE" ]; then
  export $(grep -v '^#' "$ENV_FILE" | xargs)
  echo "INFO: .env file found and loaded from ${ENV_FILE}."
else
  echo "Warning: .env file not found at ${ENV_FILE}. Some functionalities might be limited if they depended on it."
fi

echo "Script initialized."
echo "Local image directory: ${LOCAL_IMAGE_DIR}"
echo "Local thumbnail directory: ${LOCAL_THUMBNAIL_DIR}"
echo "Lineage CSV path: ${LINEAGE_CSV_PATH}"

# Initialize Counters
count_total_unique_local_files=0
count_local_duplicate_sets=0
count_lineage_has_wp_url=0
count_lineage_missing_wp_url=0
count_not_in_lineage=0
# Thumbnail specific counters
count_thumbnails_found=0
count_thumbnails_missing=0
count_orphan_thumbnails=0
count_total_thumbnail_files=0

# Associative array to store MD5 hash as key and list of file paths as value for local files
declare -A local_files_by_md5
# Associative array to store MD5 hash as key and filepath as value (for unique local files)
declare -A unique_local_files_map # filepath -> md5 (used to count unique local files)

# --- Local Duplicate Detection Logic ---
echo ""
echo "--- Starting Local Duplicate Detection in ${LOCAL_IMAGE_DIR} ---"

if [ ! -d "$LOCAL_IMAGE_DIR" ]; then
  echo "Error: Local image directory ${LOCAL_IMAGE_DIR} does not exist."
elif ! ls "${LOCAL_IMAGE_DIR}"*.webp 1> /dev/null 2>&1; then
  echo "No .webp images found in ${LOCAL_IMAGE_DIR}."
else
  MD5_CMD=""
  if command -v md5sum &> /dev/null; then MD5_CMD="md5sum";
  elif command -v md5 &> /dev/null; then MD5_CMD="md5 -r";
  else echo "Error: No md5sum or md5 command found. Cannot check for duplicates or WordPress status via lineage."; fi

  if [ -n "$MD5_CMD" ]; then
    echo "Calculating checksums for local .webp files..."
    checksum_output_file=$(mktemp)

    if [[ "$MD5_CMD" == "md5sum" ]]; then
      find "$LOCAL_IMAGE_DIR" -type f -name "*.webp" -print0 | xargs -0 "$MD5_CMD" > "$checksum_output_file"
    else # for md5 -r on macOS
      find "$LOCAL_IMAGE_DIR" -type f -name "*.webp" -exec $MD5_CMD {} + > "$checksum_output_file"
    fi

    while read -r line; do
      checksum=$(echo "$line" | awk '{print $1}')
      filepath_full=$(echo "$line" | awk '{print $2}')
      if [[ "$MD5_CMD" == "md5 -r" ]]; then # md5 -r output: checksum filepath
          filepath_full=$(echo "$line" | awk '{$1=""; print $0}' | sed 's/^[[:space:]]*//')
      fi
      local_files_by_md5["$checksum"]+="${filepath_full}\n"
      # For counting unique files, add to unique_local_files_map if not already processed
      # (based on filepath, as a file could be listed multiple times if it's part of different duplicate sets - though less likely with md5)
      if [[ -z "${unique_local_files_map[$filepath_full]}" ]]; then
        unique_local_files_map["$filepath_full"]="$checksum"
      fi
    done < "$checksum_output_file"
    rm "$checksum_output_file"

    count_total_unique_local_files=${#unique_local_files_map[@]}

    # Count duplicate sets
    temp_found_duplicates_output=0 # To control the header print
    for checksum in "${!local_files_by_md5[@]}"; do
      file_list="${local_files_by_md5[$checksum]}"
      # Count lines in file_list string
      file_count=$(echo -e "$file_list" | sed '/^\s*$/d' | wc -l) # remove empty lines then count
      if [ "$file_count" -gt 1 ]; then
        if [ "$temp_found_duplicates_output" -eq 0 ]; then echo "Found local duplicates (identical content):"; temp_found_duplicates_output=1; fi
        echo "  Checksum: $checksum"
        echo -e "$file_list" | while read -r file_path_item; do if [ -n "$file_path_item" ]; then echo "    - $file_path_item"; fi; done
        ((count_local_duplicate_sets++))
      fi
    done
    if [ "$temp_found_duplicates_output" -eq 0 ]; then echo "No local duplicates (by content) found in ${LOCAL_IMAGE_DIR}."; fi
  fi
fi
echo "--- Local Duplicate Detection Finished ---"
echo ""

# --- WordPress Existing Image Check via Lineage File ---
echo "--- Starting WordPress Existing Image Check (via Lineage File) ---"

# Lists for detailed reporting
declare -a files_cat1_lineage_has_wp_url
declare -a files_cat2_lineage_missing_wp_url
declare -a files_cat3_not_in_lineage

if [ ! -f "$LINEAGE_CSV_PATH" ]; then
  echo "Lineage file not found at $LINEAGE_CSV_PATH. Skipping WordPress status check based on lineage."
elif [ ${#unique_local_files_map[@]} -eq 0 ]; then
    if ! ls "${LOCAL_IMAGE_DIR}"*.webp 1> /dev/null 2>&1; then
        echo "No .webp images found in ${LOCAL_IMAGE_DIR}. Nothing to check against lineage."
    else
        echo "No local file checksums calculated (e.g. md5 command missing or no files processed). Cannot check against lineage."
    fi
else
  echo "Reading lineage file: $LINEAGE_CSV_PATH"
  header=$(head -n 1 "$LINEAGE_CSV_PATH")
  IFS=',' read -r -a header_fields < <(echo "$header")

  md5_col_idx=-1
  url_col_idx=-1 # Primary URL field
  guid_col_idx=-1 # Fallback
  post_name_col_idx=-1 # Another fallback for URL presence

  for i in "${!header_fields[@]}"; do
    field_trimmed=$(echo "${header_fields[$i]}" | xargs)
    if [[ "$field_trimmed" == "md5_hash" ]]; then md5_col_idx=$((i + 1)); fi
    if [[ "$field_trimmed" == "wordpress_url" ]]; then url_col_idx=$((i + 1)); fi
    if [[ "$field_trimmed" == "guid" ]]; then guid_col_idx=$((i + 1)); fi
    if [[ "$field_trimmed" == "wordpress_post_name" ]]; then post_name_col_idx=$((i + 1)); fi
  done

  wp_indicator_col_idx=$url_col_idx
  if [ "$wp_indicator_col_idx" -eq -1 ]; then wp_indicator_col_idx=$guid_col_idx; fi
  if [ "$wp_indicator_col_idx" -eq -1 ]; then wp_indicator_col_idx=$post_name_col_idx; fi

  if [ "$md5_col_idx" -eq -1 ] || [ "$wp_indicator_col_idx" -eq -1 ]; then
    echo "Error: Required columns ('md5_hash' and 'wordpress_url'/'guid'/'wordpress_post_name') not found in CSV header: $header"
  else
    echo "Found 'md5_hash' at column $md5_col_idx and a WordPress URL indicator at column $wp_indicator_col_idx."
    declare -A lineage_md5_status # Stores md5_hash -> "has_url" or "missing_url"

    tail -n +2 "$LINEAGE_CSV_PATH" | while IFS=, read -r -a line_fields; do
        if [ "${#line_fields[@]}" -ge "$md5_col_idx" ] && [ "${#line_fields[@]}" -ge "$wp_indicator_col_idx" ]; then
            line_md5_hash="${line_fields[$((md5_col_idx-1))]}"
            line_wp_url_field="${line_fields[$((wp_indicator_col_idx-1))]}"
            if [[ -n "$(echo "$line_wp_url_field" | xargs)" ]]; then # Check if URL field is non-empty
                lineage_md5_status["$line_md5_hash"]="has_url"
            else
                lineage_md5_status["$line_md5_hash"]="missing_url" # MD5 is in lineage, but URL is missing
            fi
        fi
    done

    echo "Processed ${#lineage_md5_status[@]} unique MD5 hashes from lineage records."

    for filepath in "${!unique_local_files_map[@]}"; do
      local_md5="${unique_local_files_map[$filepath]}"
      if [[ -n "${lineage_md5_status[$local_md5]}" ]]; then # MD5 found in lineage
        if [[ "${lineage_md5_status[$local_md5]}" == "has_url" ]]; then
          files_cat1_lineage_has_wp_url+=("$filepath (MD5: $local_md5)")
          ((count_lineage_has_wp_url++))
        else # "missing_url"
          files_cat2_lineage_missing_wp_url+=("$filepath (MD5: $local_md5)")
          ((count_lineage_missing_wp_url++))
        fi
      else # MD5 not found in lineage at all
        files_cat3_not_in_lineage+=("$filepath (MD5: $local_md5)")
        ((count_not_in_lineage++))
      fi
    done

    # Detailed Reporting based on refined categories
    echo ""
    if [ ${#files_cat1_lineage_has_wp_url[@]} -gt 0 ]; then
      echo "Category 1: In Lineage & Has WP URL (Assumed on WordPress):"
      for item in "${files_cat1_lineage_has_wp_url[@]}"; do echo "  - $item"; done
    fi
    if [ ${#files_cat2_lineage_missing_wp_url[@]} -gt 0 ]; then
      echo "Category 2: In Lineage & Missing WP URL (Status Uncertain, Needs URL in Lineage):"
      for item in "${files_cat2_lineage_missing_wp_url[@]}"; do echo "  - $item"; done
    fi
    if [ ${#files_cat3_not_in_lineage[@]} -gt 0 ]; then
      echo "Category 3: Not In Lineage (Assumed New or Lineage Outdated):"
      for item in "${files_cat3_not_in_lineage[@]}"; do echo "  - $item"; done
    fi

    # Handle cases where no files fall into any category for clarity
    if [ ${#files_cat1_lineage_has_wp_url[@]} -eq 0 ] && \
       [ ${#files_cat2_lineage_missing_wp_url[@]} -eq 0 ] && \
       [ ${#files_cat3_not_in_lineage[@]} -eq 0 ] && \
       [ "$count_total_unique_local_files" -gt 0 ]; then
        echo "No local files were categorized based on lineage. This might happen if lineage is empty or no local files match."
    elif [ "$count_total_unique_local_files" -eq 0 ] && ! ls "${LOCAL_IMAGE_DIR}"*.webp 1> /dev/null 2>&1; then
        # This case is already handled by the check for "No .webp images found"
        : # Do nothing here as it's covered
    elif [ "$count_total_unique_local_files" -eq 0 ]; then
        echo "No unique local files were processed to check against lineage."
    fi
  fi
fi
echo "--- WordPress Existing Image Check (via Lineage File) Finished ---"
echo ""

# --- Thumbnail Status Checks ---
echo "--- Starting Thumbnail Status Checks ---"
# Ensure thumbnail directory exists
if [ ! -d "$LOCAL_THUMBNAIL_DIR" ]; then
  echo "Warning: Thumbnail directory ${LOCAL_THUMBNAIL_DIR} does not exist. Skipping thumbnail checks."
else
  # Check 1: For each full-size image, does a thumbnail exist?
  echo "Checking for missing thumbnails..."
  if ! ls "${LOCAL_IMAGE_DIR}"*.webp 1> /dev/null 2>&1; then
    echo "No .webp images found in ${LOCAL_IMAGE_DIR} to check for thumbnails."
  else
    for img_file in "${LOCAL_IMAGE_DIR}"*.webp; do
      base_filename=$(basename "$img_file" .webp)
      # Updated naming convention for expected thumbnail
      expected_thumb_filename="${base_filename}-h360-thumb.webp"
      expected_thumb_path="${LOCAL_THUMBNAIL_DIR}${expected_thumb_filename}"

      if [ -f "$expected_thumb_path" ]; then
        ((count_thumbnails_found++))
      else
        echo "  - Missing thumbnail for: $img_file (expected: $expected_thumb_filename)"
        ((count_thumbnails_missing++))
      fi
    done
  fi

  # Check 2: Are there any orphan thumbnails?
  echo ""
  echo "Checking for orphan thumbnails..."
  # Updated pattern to find new thumbnail naming convention
  if ! ls "${LOCAL_THUMBNAIL_DIR}"*-h360-thumb.webp 1> /dev/null 2>&1; then
    echo "No thumbnail files matching '*-h360-thumb.webp' found in ${LOCAL_THUMBNAIL_DIR} to check for orphans."
  else
    # Iterate through files matching the new thumbnail naming convention
    for thumb_file in "${LOCAL_THUMBNAIL_DIR}"*-h360-thumb.webp; do
      ((count_total_thumbnail_files++)) # Count all actual thumbnail files matching the pattern
      # Derive original image stem by removing the new suffix
      thumb_basename=$(basename "$thumb_file" -h360-thumb.webp)
      expected_img_filename="${thumb_basename}.webp"
      expected_img_path="${LOCAL_IMAGE_DIR}${expected_img_filename}"

      if [ ! -f "$expected_img_path" ]; then
        echo "  - Orphan thumbnail found: $thumb_file (no corresponding image: $expected_img_filename)"
        ((count_orphan_thumbnails++))
      fi
    done
  fi
  # This check might need adjustment or can be removed if only '*-h360-thumb.webp' files are considered thumbnails.
  # It was intended to note if other .webp files exist that don't match the pattern.
  # For now, keeping it to see if any non-h360-thumb.webp files are present.
  general_webp_files_in_thumb_dir=$(ls "${LOCAL_THUMBNAIL_DIR}"*.webp 2>/dev/null | wc -l)
  if [ "$count_total_thumbnail_files" -eq 0 ] && [ "$general_webp_files_in_thumb_dir" -gt 0 ]; then
    echo "Note: .webp files are present in ${LOCAL_THUMBNAIL_DIR}, but none match the '*-h360-thumb.webp' pattern for orphan checking."
  fi

fi
echo "--- Thumbnail Status Checks Finished ---"
echo ""


# --- Summary Statistics ---
echo "--- Summary ---"
echo "Total unique .webp files processed in ${LOCAL_IMAGE_DIR}: $count_total_unique_local_files"
echo ""
echo "Local Duplicates:"
echo "  - Sets of duplicate files found (by content): $count_local_duplicate_sets"
echo ""
echo "WordPress Status (based on ${LINEAGE_CSV_PATH}):"
echo "  - On WordPress (In Lineage & Has WP URL): $count_lineage_has_wp_url"
echo "  - In Lineage, Awaiting WP URL: $count_lineage_missing_wp_url"
echo "  - Not In Lineage (New/Unexpected or Lineage Outdated): $count_not_in_lineage"
echo ""
echo "Thumbnail Status (linking ${LOCAL_IMAGE_DIR} and ${LOCAL_THUMBNAIL_DIR}):"
echo "  - Total full-size images checked for thumbnails: $((count_thumbnails_found + count_thumbnails_missing))"
echo "  - Thumbnails found for full-size images (expected format 'original_stem-h360-thumb.webp'): $count_thumbnails_found"
echo "  - Thumbnails missing for full-size images: $count_thumbnails_missing"
echo "  - Total actual thumbnail files ('*-h360-thumb.webp') found in ${LOCAL_THUMBNAIL_DIR}: $count_total_thumbnail_files"
echo "  - Orphan thumbnails (thumbnail exists, but full-size image is missing): $count_orphan_thumbnails"
echo ""

exit 0
