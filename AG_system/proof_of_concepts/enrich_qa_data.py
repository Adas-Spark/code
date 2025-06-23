import json
import argparse
import os
from typing import Dict, List, Any, Optional

# python enrich_qa_data.py generated_qa_pairs_combined_clean_20250603_214922.json /Users/joelswenson/Documents/Adas_spark/code_repo/github_repo__called_code/code/AG_system/scraping/scraped_data.json generated_qa_pairs_combined_clean_20250603_214922_enriched.json

# Constant for the site ID, as discussed.
# This is used to construct the source_url.
CARINGBRIDGE_SITE_ID = "6f33ada9-525c-3ce3-be6f-34b647b78d2d"
BASE_URL = f"https://www.caringbridge.org/site/{CARINGBRIDGE_SITE_ID}/post"

def validate_file_exists(filepath: str) -> bool:
    """Validates that a file exists and is readable."""
    if not os.path.exists(filepath):
        print(f"Error: File does not exist: {filepath}")
        return False
    if not os.path.isfile(filepath):
        print(f"Error: Path is not a file: {filepath}")
        return False
    if not os.access(filepath, os.R_OK):
        print(f"Error: File is not readable: {filepath}")
        return False
    return True

def validate_output_path(filepath: str) -> bool:
    """Validates that the output path is writable."""
    directory = os.path.dirname(filepath)
    if directory and not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")
        except OSError as e:
            print(f"Error: Cannot create directory {directory}: {e}")
            return False
    
    # Check if we can write to the directory
    test_dir = directory if directory else '.'
    if not os.access(test_dir, os.W_OK):
        print(f"Error: Cannot write to directory: {test_dir}")
        return False
    
    return True

def load_json_file(filepath: str) -> Optional[Any]:
    """Loads a JSON file with enhanced error handling."""
    if not validate_file_exists(filepath):
        return None
        
    try:
        # Try with 'utf-8-sig' first to handle potential BOM
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
            print(f"Successfully loaded {filepath}")
            return data
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath}. Details: {e.msg} (line {e.lineno}, column {e.colno})")
        # As a fallback, try 'utf-8' if 'utf-8-sig' fails for reasons other than BOM
        try:
            print(f"Attempting fallback to 'utf-8' encoding for {filepath}")
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"Successfully loaded {filepath} with utf-8 fallback")
                return data
        except json.JSONDecodeError as e_utf8:
            print(f"Error: Fallback to 'utf-8' also failed for {filepath}. Details: {e_utf8.msg} (line {e_utf8.lineno}, column {e_utf8.colno})")
            return None
        except Exception as ex_utf8:
            print(f"An unexpected error occurred during 'utf-8' fallback for {filepath}: {ex_utf8}")
            return None
    except Exception as ex:
        print(f"An unexpected error occurred while loading {filepath}: {ex}")
        return None

def validate_qa_data_structure(data: Any) -> bool:
    """Validates the structure of QA data."""
    if not isinstance(data, list):
        print("Error: QA data must be a list at the root level")
        return False
    
    if len(data) == 0:
        print("Warning: QA data is empty")
        return True
    
    # Check a sample of entries for expected structure
    sample_size = min(3, len(data))
    for i in range(sample_size):
        entry = data[i]
        if not isinstance(entry, dict):
            print(f"Error: QA entry {i} is not a dictionary")
            return False
        
        if 'answers' in entry:
            if not isinstance(entry['answers'], list):
                print(f"Error: QA entry {i} 'answers' field is not a list")
                return False
            
            # Check answer structure
            for j, answer in enumerate(entry['answers'][:2]):  # Check first 2 answers
                if not isinstance(answer, dict):
                    print(f"Error: Answer {j} in QA entry {i} is not a dictionary")
                    return False
    
    print(f"QA data structure validation passed. Found {len(data)} question blocks.")
    return True

def validate_scraped_data_structure(data: Any) -> bool:
    """Validates the structure of scraped data."""
    if not isinstance(data, list):
        print("Error: Scraped data must be a list at the root level")
        return False
    
    if len(data) == 0:
        print("Warning: Scraped data is empty")
        return True
    
    # Check that posts have post_id field
    posts_with_id = 0
    sample_size = min(10, len(data))
    
    for i in range(sample_size):
        post = data[i]
        if not isinstance(post, dict):
            print(f"Error: Scraped data entry {i} is not a dictionary")
            return False
        
        if 'post_id' in post:
            posts_with_id += 1
        else:
            print(f"Warning: Scraped data entry {i} missing 'post_id' field")
    
    if posts_with_id == 0:
        print("Error: No posts found with 'post_id' field in scraped data sample")
        return False
    
    print(f"Scraped data structure validation passed. Found {len(data)} posts, {posts_with_id}/{sample_size} sampled posts have post_id.")
    return True

def create_post_lookup(scraped_data: List[Dict]) -> tuple[Dict[str, Dict], Dict[str, Dict]]:
    """
    Creates lookup dictionaries for scraped posts and comments by their IDs.
    
    Returns:
        tuple: (post_lookup, comment_lookup)
            - post_lookup: Dict mapping post_id -> post data
            - comment_lookup: Dict mapping comment_id -> parent post data
    """
    scraped_posts = {}
    comment_to_post = {}
    skipped_posts = 0
    total_comments = 0
    total_replies = 0
    
    for i, post in enumerate(scraped_data):
        if not isinstance(post, dict):
            print(f"Warning: Skipping non-dictionary post at index {i}")
            skipped_posts += 1
            continue
            
        if 'post_id' not in post:
            print(f"Warning: Skipping post at index {i} - missing 'post_id' field")
            skipped_posts += 1
            continue
            
        post_id = post['post_id']
        if not isinstance(post_id, str) or not post_id.strip():
            print(f"Warning: Skipping post at index {i} - invalid post_id: {post_id}")
            skipped_posts += 1
            continue
            
        # Add post to lookup
        scraped_posts[post_id] = post
        
        # Process comments and replies to map comment_ids to parent post
        if 'comments' in post and isinstance(post['comments'], list):
            for comment in post['comments']:
                if isinstance(comment, dict) and 'comment_id' in comment:
                    comment_id = comment['comment_id']
                    if isinstance(comment_id, str) and comment_id.strip():
                        comment_to_post[comment_id] = post
                        total_comments += 1
                    
                    # Process replies within comments
                    if 'replies' in comment and isinstance(comment['replies'], list):
                        for reply in comment['replies']:
                            if isinstance(reply, dict) and 'comment_id' in reply:
                                reply_id = reply['comment_id']
                                if isinstance(reply_id, str) and reply_id.strip():
                                    comment_to_post[reply_id] = post
                                    total_replies += 1
    
    print(f"Created lookup for {len(scraped_posts)} posts, {total_comments} comments, and {total_replies} replies.")
    print(f"Skipped {skipped_posts} invalid entries.")
    return scraped_posts, comment_to_post

def save_json_file(data: Any, filepath: str) -> bool:
    """Saves data to a JSON file with validation."""
    if not validate_output_path(filepath):
        return False
        
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Successfully saved enriched data to {filepath}")
        return True
    except IOError as e:
        print(f"Error: Could not write to file at {filepath}: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error while saving to {filepath}: {e}")
        return False

def enrich_qa_data(qa_filepath: str, scraped_data_filepath: str, output_filepath: str) -> bool:
    """
    Enriches QA data with source titles and URLs from scraped data.

    Args:
        qa_filepath (str): Path to the input QA pairs JSON file.
        scraped_data_filepath (str): Path to the scraped data JSON file.
        output_filepath (str): Path to save the enriched QA pairs JSON file.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    print("Starting QA data enrichment process...")
    
    # Load and validate input files
    qa_data = load_json_file(qa_filepath)
    scraped_data_raw = load_json_file(scraped_data_filepath)

    if qa_data is None or scraped_data_raw is None:
        print("Error: Failed to load input files. Exiting.")
        return False

    # Validate data structures
    if not validate_qa_data_structure(qa_data):
        print("Error: QA data structure validation failed. Exiting.")
        return False
        
    if not validate_scraped_data_structure(scraped_data_raw):
        print("Error: Scraped data structure validation failed. Exiting.")
        return False

    # Create lookup dictionaries with validation
    scraped_posts, comment_to_post = create_post_lookup(scraped_data_raw)
    if not scraped_posts:
        print("Error: No valid posts found in scraped data. Exiting.")
        return False

    # Process QA data
    enriched_qa_data = []
    total_answers_processed = 0
    total_answers_enriched = 0
    
    # Enhanced diagnostic counters
    answers_with_source_field = 0
    answers_without_source_field = 0
    answers_with_empty_source = 0
    answers_with_string_source = 0
    answers_with_list_source = 0
    answers_with_other_source_type = 0
    answers_with_valid_source_format = 0

    for question_idx, question_block in enumerate(qa_data):
        if not isinstance(question_block, dict):
            print(f"Warning: Skipping non-dictionary question block at index {question_idx}")
            continue
            
        enriched_answers = []
        
        if 'answers' in question_block and isinstance(question_block['answers'], list):
            for answer_idx, answer in enumerate(question_block['answers']):
                if not isinstance(answer, dict):
                    print(f"Warning: Skipping non-dictionary answer {answer_idx} in question {question_idx}")
                    continue
                    
                total_answers_processed += 1
                
                # Enhanced diagnostic: Check source_post_id field existence and validity
                if "source_post_id" not in answer:
                    answers_without_source_field += 1
                    print(f"Debug: Missing source_post_id field in Question {question_idx}, Answer {answer_idx}")
                    source_post_ids_str = ""
                else:
                    answers_with_source_field += 1
                    source_post_ids_str = answer.get("source_post_id", "")
                    
                    # Enhanced type checking
                    if not source_post_ids_str:
                        answers_with_empty_source += 1
                        print(f"Debug: Empty source_post_id in Question {question_idx}, Answer {answer_idx}")
                    elif isinstance(source_post_ids_str, str):
                        answers_with_string_source += 1
                        cleaned_ids = [pid.strip() for pid in source_post_ids_str.split(',') if pid.strip()]
                        if cleaned_ids:
                            answers_with_valid_source_format += 1
                        else:
                            answers_with_empty_source += 1
                    elif isinstance(source_post_ids_str, list):
                        answers_with_list_source += 1
                        valid_ids = [str(pid).strip() for pid in source_post_ids_str if str(pid).strip()]
                        if valid_ids:
                            answers_with_valid_source_format += 1
                        else:
                            answers_with_empty_source += 1
                    else:
                        answers_with_other_source_type += 1
                        try:
                            if str(source_post_ids_str).strip():
                                answers_with_valid_source_format += 1
                        except:
                            answers_with_empty_source += 1

                current_titles = []
                current_urls = []
                found_sources = 0

                # Enhanced source_post_id processing - original data is never modified
                source_post_id_list = []

                if source_post_ids_str:
                    if isinstance(source_post_ids_str, str):
                        # Handle comma-separated string format
                        source_post_id_list = [pid.strip() for pid in source_post_ids_str.split(',') if pid.strip()]
                    elif isinstance(source_post_ids_str, list):
                        # Handle list format - process each item (original data preserved)
                        source_post_id_list = [str(pid).strip() for pid in source_post_ids_str if str(pid).strip()]
                        print(f"Info: Processing list-format source_post_id in Question {question_idx}, Answer {answer_idx} (original preserved)")
                    else:
                        # Handle other types by attempting string conversion
                        try:
                            source_post_id_list = [str(source_post_ids_str).strip()]
                            print(f"Info: Processing {type(source_post_ids_str)} source_post_id in Question {question_idx}, Answer {answer_idx} (original preserved)")
                        except:
                            print(f"Warning: Could not process source_post_id of type {type(source_post_ids_str)} in Question {question_idx}, Answer {answer_idx}")
                            source_post_id_list = []

                for post_id in source_post_id_list:
                    # First, try to find as a post
                    post_info = scraped_posts.get(post_id)
                    if post_info:
                        current_titles.append(post_info.get("title", ""))
                        current_urls.append(f"{BASE_URL}/{post_id}")
                        found_sources += 1
                    else:
                        # If not found as post, try to find as comment/reply
                        comment_parent_post = comment_to_post.get(post_id)
                        if comment_parent_post:
                            # Use parent post's title and construct URL from parent post's ID
                            current_titles.append(comment_parent_post.get("title", ""))
                            parent_post_id = comment_parent_post.get("post_id", "")
                            if parent_post_id:
                                current_urls.append(f"{BASE_URL}/{parent_post_id}")
                            else:
                                current_urls.append("")
                            found_sources += 1
                            print(f"Info: Found comment/reply ID '{post_id}' in post '{parent_post_id}' (Question {question_idx}, Answer {answer_idx})")
                        else:
                            print(f"Warning: ID '{post_id}' not found as post, comment, or reply (Question {question_idx}, Answer {answer_idx})")
                            # Append placeholders to maintain alignment
                            current_titles.append("")
                            current_urls.append("")

                # Add new enrichment fields only - original source_post_id field is preserved unchanged
                answer["source_title"] = current_titles
                answer["source_url"] = current_urls
                
                if found_sources > 0:
                    total_answers_enriched += 1

                enriched_answers.append(answer)

            question_block["answers"] = enriched_answers
        
        enriched_qa_data.append(question_block)

    # Save results
    success = save_json_file(enriched_qa_data, output_filepath)
    
    if success:
        print(f"\nEnrichment Summary:")
        print(f"  - Total questions processed: {len(enriched_qa_data)}")
        print(f"  - Total answers processed: {total_answers_processed}")
        print(f"  - Total answers enriched: {total_answers_enriched}")
        print(f"  - Enrichment rate: {(total_answers_enriched/total_answers_processed)*100:.1f}%" if total_answers_processed > 0 else "  - No answers to process")
        
        print(f"\nEnhanced Diagnostic Breakdown:")
        print(f"  - Answers with source_post_id field: {answers_with_source_field}")
        print(f"  - Answers without source_post_id field: {answers_without_source_field}")
        print(f"  - Answers with empty source_post_id: {answers_with_empty_source}")
        print(f"  - Answers with string source_post_id: {answers_with_string_source}")
        print(f"  - Answers with list source_post_id: {answers_with_list_source}")
        print(f"  - Answers with other source_post_id types: {answers_with_other_source_type}")
        print(f"  - Answers with valid source format: {answers_with_valid_source_format}")
        print(f"  - Expected enrichable answers: {answers_with_valid_source_format}")
        print(f"  - Actual enriched answers: {total_answers_enriched}")
        if answers_with_valid_source_format > 0:
            print(f"  - Success rate for valid sources: {(total_answers_enriched/answers_with_valid_source_format)*100:.1f}%")
    
    return success

def main():
    parser = argparse.ArgumentParser(
        description="Enrich QA JSON data with source titles and URLs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python enrich_qa_data.py qa_pairs.json scraped_data.json output.json
  python enrich_qa_data.py data/qa.json data/scraped.json results/enriched_qa.json
        """
    )
    parser.add_argument("qa_input_filepath", 
                       help="Path to the input QA JSON file")
    parser.add_argument("scraped_data_filepath", 
                       help="Path to the scraped data JSON file")
    parser.add_argument("output_filepath", 
                       help="Path to save the enriched output JSON file")
    parser.add_argument("--validate-only", 
                       action="store_true",
                       help="Only validate input files without processing")

    args = parser.parse_args()

    # Basic validation for file extensions
    for filepath in [args.qa_input_filepath, args.scraped_data_filepath, args.output_filepath]:
        if not filepath.endswith('.json'):
            print(f"Warning: {filepath} does not have .json extension")

    # Validate input files exist
    if not validate_file_exists(args.qa_input_filepath):
        return 1
    if not validate_file_exists(args.scraped_data_filepath):
        return 1

    if args.validate_only:
        print("Validation mode - checking file structures only...")
        qa_data = load_json_file(args.qa_input_filepath)
        scraped_data = load_json_file(args.scraped_data_filepath)
        
        if qa_data is None or scraped_data is None:
            return 1
            
        qa_valid = validate_qa_data_structure(qa_data)
        scraped_valid = validate_scraped_data_structure(scraped_data)
        
        if qa_valid and scraped_valid:
            print("✓ All validations passed!")
            return 0
        else:
            print("✗ Validation failed!")
            return 1

    # Run the enrichment process
    success = enrich_qa_data(args.qa_input_filepath, args.scraped_data_filepath, args.output_filepath)
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())