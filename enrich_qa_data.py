import json
import argparse
import os

# Constant for the site ID, as discussed.
# This is used to construct the source_url.
CARINGBRIDGE_SITE_ID = "6f33ada9-525c-3ce3-be6f-34b647b78d2d"
BASE_URL = f"https://www.caringbridge.org/site/{CARINGBRIDGE_SITE_ID}/post"

def load_json_file(filepath):
    """Loads a JSON file."""
    try:
        # Try with 'utf-8-sig' first to handle potential BOM
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Could not decode JSON from {filepath}. Details: {e.msg} (line {e.lineno}, column {e.colno})")
        # As a fallback, try 'utf-8' if 'utf-8-sig' fails for reasons other than BOM
        try:
            print(f"Attempting fallback to 'utf-8' encoding for {filepath}")
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e_utf8:
            print(f"Error: Fallback to 'utf-8' also failed for {filepath}. Details: {e_utf8.msg} (line {e_utf8.lineno}, column {e_utf8.colno})")
            return None
        except Exception as ex_utf8:
            print(f"An unexpected error occurred during 'utf-8' fallback for {filepath}: {ex_utf8}")
            return None
    except Exception as ex:
        print(f"An unexpected error occurred while loading {filepath}: {ex}")
        return None

def save_json_file(data, filepath):
    """Saves data to a JSON file."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"Successfully saved enriched data to {filepath}")
    except IOError:
        print(f"Error: Could not write to file at {filepath}")

def enrich_qa_data(qa_filepath, scraped_data_filepath, output_filepath):
    """
    Enriches QA data with source titles and URLs from scraped data.

    Args:
        qa_filepath (str): Path to the input QA pairs JSON file.
        scraped_data_filepath (str): Path to the scraped data JSON file.
        output_filepath (str): Path to save the enriched QA pairs JSON file.
    """
    qa_data = load_json_file(qa_filepath)
    scraped_posts_raw = load_json_file(scraped_data_filepath)

    if qa_data is None or scraped_posts_raw is None:
        print("Exiting due to errors loading input files.")
        return

    # Create a dictionary for quick lookup of scraped posts by post_id
    scraped_posts = {post['post_id']: post for post in scraped_posts_raw if 'post_id' in post}

    enriched_qa_data = []

    for question_block in qa_data:
        enriched_answers = []
        if 'answers' in question_block and isinstance(question_block['answers'], list):
            for answer in question_block['answers']:
                source_post_ids_str = answer.get("source_post_id", "")

                # Preserve existing source_date
                # No specific action needed here as we are just adding new fields
                # and the original answer object (with source_date) is being modified.

                current_titles = []
                current_urls = []

                if source_post_ids_str:
                    source_post_id_list = [pid.strip() for pid in source_post_ids_str.split(',')]

                    for post_id in source_post_id_list:
                        if not post_id: # Handle potential empty strings if IDs are like "id1, , id2"
                            continue

                        post_info = scraped_posts.get(post_id)
                        if post_info:
                            current_titles.append(post_info.get("title", ""))
                            current_urls.append(f"{BASE_URL}/{post_id}")
                        else:
                            print(f"Warning: Post ID '{post_id}' not found in scraped data. Skipping for title/URL enrichment for this ID.")
                            # Append placeholders or decide how to handle missing data for specific IDs
                            current_titles.append("") # Or some other placeholder like "Title Not Found"
                            current_urls.append("")   # Or some other placeholder like "URL Not Found"


                # Add new fields as string representations of lists
                answer["source_title"] = str(current_titles)
                answer["source_url"] = str(current_urls)

                enriched_answers.append(answer)

            question_block["answers"] = enriched_answers
        enriched_qa_data.append(question_block)

    save_json_file(enriched_qa_data, output_filepath)

def main():
    parser = argparse.ArgumentParser(description="Enrich QA JSON data with source titles and URLs.")
    parser.add_argument("qa_input_filepath", help="Path to the input QA JSON file (e.g., EXAMPLE_generated_qa_pairs_combined_clean_20250603_214922.json)")
    parser.add_argument("scraped_data_filepath", help="Path to the scraped data JSON file (e.g., AG_system/EXAMPLE_scraped_data_with_author_and_text_changes.json)")
    parser.add_argument("output_filepath", help="Path to save the enriched output JSON file.")

    args = parser.parse_args()

    # Basic validation for file extensions (optional, but good practice)
    if not args.qa_input_filepath.endswith('.json') or \
       not args.scraped_data_filepath.endswith('.json') or \
       not args.output_filepath.endswith('.json'):
        print("Warning: Input/output files should preferably be .json files.")

    enrich_qa_data(args.qa_input_filepath, args.scraped_data_filepath, args.output_filepath)

if __name__ == "__main__":
    main()
