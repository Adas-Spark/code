#!/usr/bin/env python3
"""
Script to update author names and text content in scraped CaringBridge JSON data.

Usage:
    python update_posts.py <scraped_data.json> <changes.json> <output.json>

Arguments:
    scraped_data.json: JSON file containing the scraped posts data
    changes.json: JSON file containing post IDs, new author names, and optional new text
    output.json: Where to save the updated data

Example:
    python update_posts.py scraped_data.json authorship_and_text_changes.json updated_data.json

The changes.json file should have this structure:
{
  "author_changes": [
    {
      "post_id": "post-id-here",
      "new_author": "Author Name",
      "new_text": "Optional new text content"  // Only if text needs to be changed
    },
    ...
  ]
}
"""

import json
import sys
import argparse

def update_posts(scraped_data_file, changes_file, output_file):
    """
    Update author names and optionally text content in scraped data based on changes file.
    
    Args:
        scraped_data_file: Path to the JSON file containing scraped data
        changes_file: Path to the JSON file containing changes
        output_file: Path to save the updated JSON data
    """
    # Read the scraped data
    try:
        with open(scraped_data_file, 'r', encoding='utf-8') as f:
            posts = json.load(f)
    except FileNotFoundError:
        print(f"Error: File {scraped_data_file} not found")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {scraped_data_file}")
        sys.exit(1)
    
    # Read the changes
    try:
        with open(changes_file, 'r', encoding='utf-8') as f:
            changes_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File {changes_file} not found")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {changes_file}")
        sys.exit(1)
    
    # Create a dictionary for faster lookup
    changes_dict = {change['post_id']: change 
                   for change in changes_data['author_changes']}
    
    # Count changes made
    author_changes_made = 0
    text_changes_made = 0
    
    # Update posts
    for post in posts:
        post_id = post.get('post_id')
        if post_id in changes_dict:
            change = changes_dict[post_id]
            
            # Update author
            old_author = post.get('author_name', 'Unknown')
            new_author = change['new_author']
            post['author_name'] = new_author
            author_changes_made += 1
            print(f"Updated author for post {post_id}: '{old_author}' -> '{new_author}'")
            
            # Update text if specified
            if 'new_text' in change:
                old_text = post.get('text', '')
                new_text = change['new_text']
                post['text'] = new_text
                text_changes_made += 1
                print(f"Updated text for post {post_id}")
    
    # Save the updated data
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)
        print(f"\nSuccessfully updated {author_changes_made} author names and {text_changes_made} text contents")
        print(f"Saved to {output_file}")
    except IOError:
        print(f"Error: Unable to write to {output_file}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='Update author names and text content in scraped CaringBridge JSON data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
    python update_posts.py scraped_data.json authorship_and_text_changes.json updated_data.json

The changes.json file should have this structure:
{
  "author_changes": [
    {
      "post_id": "post-id-here",
      "new_author": "Author Name",
      "new_text": "Optional new text content"  // Only if text needs to be changed
    },
    ...
  ]
}
        """
    )
    
    parser.add_argument('scraped_data', help='Path to the scraped data JSON file')
    parser.add_argument('changes', help='Path to the changes JSON file')
    parser.add_argument('output', help='Path where the updated JSON will be saved')
    
    args = parser.parse_args()
    
    update_posts(args.scraped_data, args.changes, args.output)

if __name__ == "__main__":
    main()
