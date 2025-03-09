import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse

def load_scraped_data(filepath):
  """Loads scraped data from a JSON file.

  Args:
    filepath: The path to the JSON file.

  Returns:
    A list of dictionaries representing the scraped data, or an empty list if the file is not found.
  """
  try:
    with open(filepath, 'r') as f:
        return json.load(f)
  except FileNotFoundError:
    return
  
def load_existing_post_ids(data):
    return {post['post_id'] for post in data}

def scrape_website_content(website_url, output_filename="scraped_data.json", cookies_filepath="cookies.json"):
    """
    Scrapes content from a website, focusing on post feeds, reactions, and comments,
    and saves the data in a structured JSON file.
    Uses Chrome profile for session persistence and injects cookies for login.
    """
    profile_path = "/Users/dez/Library/Application Support/Google/Chrome/Default"
    parsed_url = urlparse(website_url)
    website_domain_normalized = parsed_url.netloc.replace("www.", "", 1)

    options = Options()
    options.binary_location = "/Applications/Google Chrome.app"
    options.add_argument(f"user-data-dir={profile_path}")
    options.add_argument("--profile-directory=Default")
    # options.add_argument("--headless=new") #or just "--headless" for older chrome versions.

    driver = webdriver.Chrome(options=options)
    driver.get(website_url)
    wait = WebDriverWait(driver, 23)

    all_posts_data = []

    try:
        i=True
        while i==True:
            try:
                view_more_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-qa="showMoreBtn"]')))
                view_more_button.click()
                time.sleep(7)
                # i=0
            except NoSuchElementException:
                print("No more 'View More' buttons found. Loading complete.")
                break
            except TimeoutException:
                print("Timeout waiting for 'View More' button. Proceeding with loaded content.")
                break        
        all_posts_data = load_scraped_data('scraped_data.json') 
        existing_posts = load_existing_post_ids(all_posts_data)
        posts_elements = driver.find_elements(By.CSS_SELECTOR, 'article.jsx-2490229088')

        for post_element in posts_elements:
            post_data = {}
            post_data['post_id'] = post_element.get_attribute('id') if post_element.get_attribute('id') else "N/A"
            if post_data['post_id'] in existing_posts:
                print(f"Post ID {post_data['post_id']} already scraped. Skipping...")
                continue
            print(f"Post ID: {post_data['post_id']}")
            try:
                read_more_elemnt = post_element.find_element(By.CLASS_NAME, 'chakra-link.readMoreToggle')
                read_more_elemnt.click()
                time.sleep(1)
            except NoSuchElementException:
                print("No 'Read More' button found. Proceeding with visible content.")

            header_element = post_element.find_element(By.CSS_SELECTOR, 'header.jsx-145e72c7529e8da0')
            if header_element:
                author_element = header_element.find_element(By.CLASS_NAME, 'postAuthor')
                post_data['author_name'] = author_element.text.strip() if author_element else "N/A"
                date_element = header_element.find_element(By.CLASS_NAME, 'postDate')
                post_data['post_date'] = date_element.text.strip() if date_element else "N/A"

            content_element = post_element.find_element(By.CLASS_NAME, 'jsx-5f4f7e8cb6c49110.postBody')
            if content_element:
                title_container_element = post_element.find_element(By.CLASS_NAME, 'jsx-b2917769f663cb65.postTitleContainer')
                title_element = title_container_element.find_element(By.TAG_NAME, 'h1') if title_container_element else None
                post_data['title'] = title_element.text.strip() if title_element else "N/A"
                print("Title: ")
                print(post_data['title'])
                text_element = content_element.find_element(By.CLASS_NAME, 'css-0')
                post_data['text'] = text_element.text.strip() if text_element else "N/A"

                post_data['photos'] = []
                try:
                    photo_elements_div = post_element.find_element(By.CSS_SELECTOR, 'div.jsx-90dd3d5d3d6464a0.quadLayout')
                    if photo_elements_div:
                        photo_elements = photo_elements_div.find_elements(By.TAG_NAME, 'img')
                        for img in photo_elements:
                            post_data['photos'].append(img.get_attribute('src'))
                except NoSuchElementException as click_err:
                    print(f"Photo element not found: div.jsx-90dd3d5d3d6464a0.quadLayout")

            post_data['reactions'] = {}
            reactions_container_element = post_element.find_element(By.CSS_SELECTOR, 'div.jsx-2490229088.countButtons')
            post_data['reactions'] = scrape_reactions(reactions_container_element, driver, wait)

            post_data['comments'] = []
            try:
                comments_container_element = post_element.find_element(By.CSS_SELECTOR, 'button[data-qa^="toggleComments-"]')
                if comments_container_element:
                    comments_container_element.click()
                    time.sleep(2)

                    comment_items_elements = post_element.find_elements(By.CSS_SELECTOR, 'div[data-qa="comment"]')
                    for comment_item_element in comment_items_elements:
                        comment_data = scrape_comment_selenium(comment_item_element, driver, wait)
                        post_data['comments'].append(comment_data)
            except NoSuchElementException:
                print("Comment button NOT found using CSS Selector with data-qa starts-with.")
            except TimeoutException:
                print("Timeout waiting for comment button using CSS Selector with data-qa starts-with.")
            all_posts_data.append(post_data)

    except Exception as e:
        print(f"An error occurred during scraping: {e}")

    finally:
        driver.quit()

    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(all_posts_data, f, indent=4)
    print(f"Scraped data saved to '{output_filename}'")

def scrape_reactions(reactions_container_element, driver, wait):
    reactions = {}
    if reactions_container_element:
        reaction_buttons_elements = reactions_container_element.find_elements(By.CSS_SELECTOR, 'button[data-qa^="reactionCounter-"]')

        for reaction_button_element in reaction_buttons_elements:
            try:
                reaction_button_element.click()
                time.sleep(2)
                reaction_tab_elements = driver.find_elements(By.CSS_SELECTOR, 'button[data-qa^="reactionTab-"]')
                for reaction_tab in reaction_tab_elements:
                    reaction_tab.click()
                    time.sleep(1)
                    popup_soup = BeautifulSoup(driver.page_source, 'html.parser')
                    modal_container = popup_soup.find('div', class_='modalContainer')
                    reactor_names_list = modal_container.find_all('span', class_='reactorName')
                    reactors_text = []
                    for name in reactor_names_list:
                        if name:
                            reactors_text.append(name.text.strip())
                    emoji_type = reaction_tab.get_attribute('data-qa').replace("reactionTab-", "")
                    reactions[emoji_type] = {
                        'count': reaction_tab.text.strip(),
                        'reactors': reactors_text
                    }

                close_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-qa="closeModal"]')))
                driver.execute_script("arguments[0].click();", close_button)
                wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, 'div.modalContainer')))

            except NoSuchElementException as click_err:
                print(f"Reaction tab not found: button[data-qa^=\"reactionTab-\"]")
                continue
    return reactions

def scrape_comment_selenium(comment_item_element, driver, wait):
    """
    Recursively scrapes a comment, its reactions and its replies using Selenium WebElements.
    """
    comment_data = {}

    try:
        read_more_elemnt = comment_item_element.find_element(By.CLASS_NAME, 'chakra-link.readMoreToggle')
        read_more_elemnt.click()
        time.sleep(1)
    except NoSuchElementException:
        print("No 'Read More' button found. Proceeding with visible content.")

    comment_data['comment_id'] = comment_item_element.get_attribute('data-id') if comment_item_element.get_attribute('data-id') else "N/A"

    header_element = comment_item_element.find_element(By.CLASS_NAME, 'jsx-4095120822.commentHeader')
    if header_element:
        author_element = header_element.find_element(By.TAG_NAME, 'strong')
        parts = header_element.text.split('—')
        comment_data['author_name'] = parts[0].strip() if author_element else "N/A"
        comment_data['comment_date'] = parts[1].strip() if len(parts) > 1 else "N/A"

    text_element = comment_item_element.find_element(By.CLASS_NAME, 'css-0')
    comment_data['text'] = text_element.text.strip() if text_element else "N/A"

    comment_data['reactions'] = {}
    reactions_container_element = comment_item_element.find_element(By.CLASS_NAME, 'jsx-4095120822.actionButtons')
    comment_data['reactions'] = scrape_reactions(reactions_container_element, driver, wait)

    comment_data['replies'] = []
    try:
        replies_container_element = comment_item_element.find_element(By.CLASS_NAME, 'jsx-a92a6789e88cdd98.thread')
        if replies_container_element:
            try:
                reply_items_elements = replies_container_element.find_elements(By.CSS_SELECTOR, 'div[data-qa="reply"]')
                for reply_item_element in reply_items_elements:
                    reply_data = scrape_comment_selenium(reply_item_element, driver, wait)
                    comment_data['replies'].append(reply_data)
            except NoSuchElementException as click_err:
                print(f"Did not find comment reply jsx-a92a6789e88cdd98.thread")
    except NoSuchElementException as click_err:
        print(f"Did not find comment reply thread jsx-a92a6789e88cdd98.thread")

    return comment_data

if __name__ == "__main__":
    target_website_url = "https://www.caringbridge.org/site/6f33ada9-525c-3ce3-be6f-34b647b78d2d"
    scrape_website_content(target_website_url)