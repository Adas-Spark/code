#!/bin/bash

# =============================================================================
#
#                            TARGETED DEBUGGING SCRIPT
#
# PURPOSE:
# This script was created for targeted, manual debugging of the data pipeline.
# Its goal is to diagnose why specific files, known to be missing data in the
# final output, were failing to merge correctly.
#
# HOW IT WORKS:
# The script iterates through a hard-coded list of problematic filenames.
# For each filename, it performs two separate 'grep' searches to find the
# corresponding key in the two source CSV files:
#
#   1. 'processing_lineage.csv': The output from the local image processor.
#   2. 'wordpress_urls.csv': The data downloaded from the remote server.
#
# By displaying the matching keys from both files side-by-side, this script
# allows for a direct visual comparison, making it easy to spot subtle
# discrepancies like case-sensitivity (e.g., 'IMG' vs 'img'), character
# substitution (e.g., ' ' vs '-'), or special character handling (e.g., '~').
#
# This tool was instrumental in identifying that the filename "keys" needed
# to be normalized (lowercased, spaces and tildes replaced) before the
# final merge could succeed.
#
# =============================================================================

# A simple, targeted script to check a specific list of 5 files
# against the two source CSVs.

# --- Configuration: Define the paths to the files we are checking ---
PROCESSING_LINEAGE_FILE="lineage/processing_lineage.csv"
WORDPRESS_URLS_FILE="lineage/wordpress_urls.csv"

echo "🔬 Starting targeted check on 5 specific files..."

# --- Loop through the provided list of filenames ---
for webp_filename in \
  "20210110_100157~3-adasstory.webp" \
  "IMG_2810 Copy-adasstory.webp" \
  "Ada Swenson 1247851-8400-adasstory.webp" \
  "20210704_102422 Copy~2-adasstory.webp" \
  "IMG_2715 Copy-adasstory.webp"
do
    # Get the stem of the filename to use as a search key
    # Quoting "$webp_filename" is important to handle spaces correctly
    file_stem=$(echo "$webp_filename" | sed 's/\.webp$//')

    echo ""
    echo "=================================================="
    echo "🕵️  Checking for stem: '$file_stem'"
    echo "=================================================="

    # Test 1: How the key appears in the processing lineage
    echo "1. Result from 'processing_lineage.csv':"
    # Grep for the stem (case-insensitive) and show the whole line for context
    grep -i "$file_stem" "$PROCESSING_LINEAGE_FILE"
    if ! grep -q -i "$file_stem" "$PROCESSING_LINEAGE_FILE"; then
        echo "(No match found)"
    fi
    echo "---"

    # Test 2: How the key appears in the WordPress URL list
    echo "2. Result from 'wordpress_urls.csv':"
    # Grep for the stem (case-insensitive) and show the whole line
    grep -i "$file_stem" "$WORDPRESS_URLS_FILE"
    if ! grep -q -i "$file_stem" "$WORDPRESS_URLS_FILE"; then
        echo "(No match found)"
    fi
done

echo ""
echo "✅ Targeted check complete."
