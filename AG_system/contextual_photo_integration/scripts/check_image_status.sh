#!/usr/bin/env bash

# --- Safety Check: Ensure this script is run with a modern bash version ---
if ! declare -A &>/dev/null; then
  echo "ERROR: This script requires a modern version of bash that supports associative arrays."
  echo "Please run it using 'bash scripts/check_image_status.sh' or './scripts/check_image_status.sh'."
  exit 1
fi

# --- Define Paths ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INTEGRATION_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Build all paths from the integration root for accuracy
ENV_FILE="${INTEGRATION_ROOT}/.env"
LOCAL_IMAGE_DIR="${INTEGRATION_ROOT}/processed_webp/"
LOCAL_THUMBNAIL_DIR="${INTEGRATION_ROOT}/processed_webp_thumbnails/"
LINEAGE_CSV_PATH="${INTEGRATION_ROOT}/lineage/complete_image_lineage.csv"

# Load configuration from .env file
if [ -f "$ENV_FILE" ]; then
  set -a; source "$ENV_FILE"; set +a
  echo "INFO: .env file found and loaded from ${ENV_FILE}."
else
  echo "Warning: .env file not found at ${ENV_FILE}."
fi

echo "Script initialized."
echo "Local image directory: ${LOCAL_IMAGE_DIR}"
echo "Local thumbnail directory: ${LOCAL_THUMBNAIL_DIR}"
echo "Lineage CSV path: ${LINEAGE_CSV_PATH}"

# Initialize Counters
count_total_unique_local_files=0; count_local_duplicate_sets=0
count_lineage_has_wp_url=0; count_lineage_missing_wp_url=0; count_not_in_lineage=0
count_thumbnails_found=0; count_thumbnails_missing=0; count_orphan_thumbnails=0; count_total_thumbnail_files=0

# Associative arrays
declare -A local_files_by_md5
declare -A unique_local_files_map

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
  else echo "Error: No md5sum or md5 command found."; exit 1; fi

  echo "Calculating checksums for local .webp files..."
  while IFS= read -r -d $'\0' filepath_full; do
    checksum=$($MD5_CMD "$filepath_full" | awk '{print $1}')
    local_files_by_md5["$checksum"]+="${filepath_full}"$'\n'
    unique_local_files_map["$filepath_full"]="$checksum"
  done < <(find "$LOCAL_IMAGE_DIR" -type f -name "*.webp" -print0)
  count_total_unique_local_files=${#unique_local_files_map[@]}

  temp_found_duplicates_output=0
  for checksum in "${!local_files_by_md5[@]}"; do
    file_list="${local_files_by_md5[$checksum]}"
    file_count=$(echo -e "$file_list" | sed '/^\s*$/d' | wc -l)
    if [ "$file_count" -gt 1 ]; then
      if [ "$temp_found_duplicates_output" -eq 0 ]; then echo "Found local duplicates (identical content):"; temp_found_duplicates_output=1; fi
      echo "  Checksum: $checksum"
      echo -e "$file_list" | while read -r file_path_item; do if [ -n "$file_path_item" ]; then echo "    - $file_path_item"; fi; done
      ((count_local_duplicate_sets++))
    fi
  done
  if [ "$temp_found_duplicates_output" -eq 0 ]; then echo "No local duplicates (by content) found in ${LOCAL_IMAGE_DIR}."; fi
fi
echo "--- Local Duplicate Detection Finished ---"
echo ""

# --- WordPress Existing Image Check via Lineage File ---
echo "--- Starting WordPress Existing Image Check (via Lineage File) ---"

declare -a files_cat1_lineage_has_wp_url
declare -a files_cat2_lineage_missing_wp_url
declare -a files_cat3_not_in_lineage

if [ ! -f "$LINEAGE_CSV_PATH" ]; then
  echo "Lineage file not found at $LINEAGE_CSV_PATH."
  echo "Categorizing all found local files as 'Not In Lineage'."
  for filepath in "${!unique_local_files_map[@]}"; do
    local_md5="${unique_local_files_map[$filepath]}"
    files_cat3_not_in_lineage+=("$filepath (MD5: $local_md5)")
  done
  count_not_in_lineage=${#files_cat3_not_in_lineage[@]}

elif [ ${#unique_local_files_map[@]} -eq 0 ]; then
  echo "No unique local files processed. Nothing to check against lineage."
else
  echo "Reading lineage file: $LINEAGE_CSV_PATH"
  read -r header < "$LINEAGE_CSV_PATH"
  IFS=',' read -r -a header_fields <<< "$header"

  md5_col_idx=-1; url_col_idx=-1; guid_col_idx=-1; post_name_col_idx=-1

  for i in "${!header_fields[@]}"; do
    field_trimmed=$(echo "${header_fields[$i]}" | tr -d '[:space:]"')
    if [[ "$field_trimmed" == "md5_hash" ]]; then md5_col_idx=$i; fi
    if [[ "$field_trimmed" == "wordpress_url" || "$field_trimmed" == "url" ]]; then url_col_idx=$i; fi
    if [[ "$field_trimmed" == "guid" ]]; then guid_col_idx=$i; fi
    if [[ "$field_trimmed" == "wordpress_post_name" ]]; then post_name_col_idx=$i; fi
  done

  wp_indicator_col_idx=$url_col_idx
  if [ "$wp_indicator_col_idx" -eq -1 ]; then wp_indicator_col_idx=$guid_col_idx; fi
  if [ "$wp_indicator_col_idx" -eq -1 ]; then wp_indicator_col_idx=$post_name_col_idx; fi
  
  # Note: md5_col_idx will be 0, url_col_idx will be 20 based on your file.

  if [ "$md5_col_idx" -eq -1 ] || [ "$wp_indicator_col_idx" -eq -1 ]; then
    echo "Error: Required columns ('md5_hash' and a URL indicator) not found in CSV header."
  else
    echo "Found 'md5_hash' at column $((md5_col_idx + 1)) and a WordPress URL indicator at column $((wp_indicator_col_idx + 1))."
    declare -A lineage_md5_status
    
    # --- ROBUST CSV PARSING ---
    tail -n +2 "$LINEAGE_CSV_PATH" | while IFS=',' read -r -a line_fields; do
      line_md5_hash="${line_fields[$md5_col_idx]}"
      line_wp_url_field="${line_fields[$wp_indicator_col_idx]}"
      if [[ -n "$(echo "$line_wp_url_field" | tr -d '[:space:]')" ]]; then
        lineage_md5_status["$line_md5_hash"]="has_url"
      else
        lineage_md5_status["$line_md5_hash"]="missing_url"
      fi
    done

    echo "Processed ${#lineage_md5_status[@]} unique MD5 hashes from lineage records."

    for filepath in "${!unique_local_files_map[@]}"; do
      local_md5="${unique_local_files_map[$filepath]}"
      if [[ -v lineage_md5_status[$local_md5] ]]; then
        if [[ "${lineage_md5_status[$local_md5]}" == "has_url" ]]; then
          files_cat1_lineage_has_wp_url+=("$filepath (MD5: $local_md5)")
        else
          files_cat2_lineage_missing_wp_url+=("$filepath (MD5: $local_md5)")
        fi
      else
        files_cat3_not_in_lineage+=("$filepath (MD5: $local_md5)")
      fi
    done
    count_lineage_has_wp_url=${#files_cat1_lineage_has_wp_url[@]}
    count_lineage_missing_wp_url=${#files_cat2_lineage_missing_wp_url[@]}
    count_not_in_lineage=${#files_cat3_not_in_lineage[@]}
  fi
fi

# Detailed Reporting based on refined categories
echo ""
if [ ${#files_cat1_lineage_has_wp_url[@]} -gt 0 ]; then
  echo "Category 1: In Lineage & Has WP URL (Assumed on WordPress):"
  for item in "${files_cat1_lineage_has_wp_url[@]}"; do echo "  - $item"; done
fi
if [ ${#files_cat2_lineage_missing_wp_url[@]} -gt 0 ]; then
  echo "Category 2: In Lineage & Missing WP URL (Needs URL in Lineage):"
  for item in "${files_cat2_lineage_missing_wp_url[@]}"; do echo "  - $item"; done
fi
if [ ${#files_cat3_not_in_lineage[@]} -gt 0 ]; then
  echo "Category 3: Not In Lineage (Ready for Upload):"
  for item in "${files_cat3_not_in_lineage[@]}"; do echo "  - $item"; done
fi

echo "--- WordPress Existing Image Check (via Lineage File) Finished ---"
echo ""

# --- Thumbnail Status Checks ---
echo "--- Starting Thumbnail Status Checks ---"
if [ ! -d "$LOCAL_THUMBNAIL_DIR" ]; then
  echo "Warning: Thumbnail directory ${LOCAL_THUMBNAIL_DIR} does not exist."
else
  echo "Checking for missing thumbnails..."
  for img_file in "${LOCAL_IMAGE_DIR}"*.webp; do
    base_filename=$(basename "$img_file" .webp)
    expected_thumb_filename="${base_filename}-h360-thumb.webp"
    expected_thumb_path="${LOCAL_THUMBNAIL_DIR}${expected_thumb_filename}"
    if [ -f "$expected_thumb_path" ]; then
      ((count_thumbnails_found++))
    else
      echo "  - Missing thumbnail for: $img_file (expected: $expected_thumb_filename)"
      ((count_thumbnails_missing++))
    fi
  done

  echo ""
  echo "Checking for orphan thumbnails..."
  for thumb_file in "${LOCAL_THUMBNAIL_DIR}"*-h360-thumb.webp; do
    ((count_total_thumbnail_files++))
    thumb_basename=$(basename "$thumb_file" -h360-thumb.webp)
    expected_img_filename="${thumb_basename}.webp"
    expected_img_path="${LOCAL_IMAGE_DIR}${expected_img_filename}"
    if [ ! -f "$expected_img_path" ]; then
      echo "  - Orphan thumbnail found: $thumb_file (no corresponding image: $expected_img_filename)"
      ((count_orphan_thumbnails++))
    fi
  done
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
echo "  - Not In Lineage (New/Ready for Upload): $count_not_in_lineage"
echo ""
echo "Thumbnail Status (linking ${LOCAL_IMAGE_DIR} and ${LOCAL_THUMBNAIL_DIR}):"
echo "  - Total images checked for thumbnails: $((count_thumbnails_found + count_thumbnails_missing))"
echo "  - Thumbnails found for full-size images: $count_thumbnails_found"
echo "  - Thumbnails missing for full-size images: $count_thumbnails_missing"
echo "  - Total thumbnail files ('*-h360-thumb.webp') found: $count_total_thumbnail_files"
echo "  - Orphan thumbnails (thumbnail exists, but full-size image is missing): $count_orphan_thumbnails"
echo ""

exit 0