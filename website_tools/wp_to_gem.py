import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# 1. Validate that an input file was provided
if len(sys.argv) < 2:
    print("❌ Error: Missing input file.")
    print("Usage: python3 wp_to_gem.py <your_wordpress_file.xml>")
    sys.exit(1)

input_path = Path(sys.argv[1])

# Check if the file actually exists before processing
if not input_path.exists():
    print(f"❌ Error: File '{input_path}' not found.")
    sys.exit(1)

# 2. Dynamically generate the output filename
# input_path.stem extracts everything before the final extension (e.g., 'smphinformatics.WordPress.2026-07-10')
output_path = input_path.with_name(f"{input_path.stem}_cleaned_for_gem.txt")

# Define the WordPress XML namespaces
namespaces = {
    'wp': 'http://wordpress.org/export/1.2/',
    'content': 'http://purl.org/rss/1.0/modules/content/'
}

print(f"Parsing WordPress XML: {input_path.name}...")

try:
    tree = ET.parse(input_path)
    root = tree.getroot()
except ET.ParseError as e:
    print(f"❌ Error parsing XML file. Is it corrupted? Details: {e}")
    sys.exit(1)

# Find all items (posts, pages, attachments)
items = root.findall('.//item')
compiled_pages = 0

print("Filtering and extracting published pages...")
with open(output_path, 'w', encoding='utf-8') as f:
    for item in items:
        post_type = item.find('wp:post_type', namespaces)
        status = item.find('wp:status', namespaces)
        
        # Guard rails: Only grab live pages (ignore attachments, blog posts, and drafts)
        if post_type is not None and post_type.text == 'page':
            if status is not None and status.text == 'publish':
                title_elem = item.find('title')
                title = title_elem.text if title_elem is not None and title_elem.text else "Untitled Page"
                
                content_elem = item.find('content:encoded', namespaces)
                content = content_elem.text if content_elem is not None and content_elem.text else ""
                
                # Write to our master document with clean dividers
                f.write(f"--- PAGE START: {title} ---\n\n")
                f.write(content)
                f.write("\n\n--- PAGE END ---\n\n")
                compiled_pages += 1

print(f"✨ Success! Compiled {compiled_pages} public pages into '{output_path.name}'.")
