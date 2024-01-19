#!/usr/bin/python3
import os
import requests
import json
import argparse
from markdown import markdown
from bs4 import BeautifulSoup

# Argument Parser Setup
parser = argparse.ArgumentParser(description='Import Markdown files into Discourse')
parser.add_argument('-c', '--category', type=int, help='Category ID for the Discourse posts')
parser.add_argument('-d', '--directory', type=str, help='Directory containing Markdown files')
parser.add_argument('-f', '--file', type=str, help='Path to a single Markdown file')
parser.add_argument('-l', '--list-categories', action='store_true', help='List available categories in Discourse')
parser.add_argument('-t', '--test-connection', action='store_true', help='Test connection to Discourse')
parser.add_argument('--debug', action='store_true', help='Enable debug mode to see requests and responses from Discourse API')
parser.add_argument('--preview', type=str, help='Preview the processing of a single Markdown file')
args = parser.parse_args()

# Check if the config file exists
config_file_path = 'config.json'
if not os.path.isfile(config_file_path):
    print(f"Configuration file '{config_file_path}' not found.")
    exit(1)

# Load configuration from JSON file
with open(config_file_path, 'r') as config_file:
    config = json.load(config_file)

DISCOURSE_API_KEY = config['discourse_api_key']
DISCOURSE_API_USERNAME = config['discourse_api_username']
DISCOURSE_URL = config['discourse_url']
CATEGORY_ID = args.category

def debug_print(message):
    if args.debug:
        print(message)

def get_first_header(markdown_text):
    # Convert Markdown to HTML
    html = markdown(markdown_text)

    # Parse HTML to find the first header
    soup = BeautifulSoup(html, 'html.parser')
    headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    if headers:
        return headers[0].get_text()
    return None

import urllib.parse

def check_duplicate_topic(title, category_id):
    encoded_title = urllib.parse.quote(title)
    url = f'{DISCOURSE_URL}/search.json?q=title:"{encoded_title}"&page=1'
    headers = {'Api-Key': DISCOURSE_API_KEY, 'Api-Username': DISCOURSE_API_USERNAME}
    debug_print(f"Connecting to: {url}")

    response = requests.get(url, headers=headers)

    # Debug print to see the status code and response text
    debug_print(f"Status Code: {response.status_code}")
    debug_print(f"Response Text: {response.text}")

    # Check if the response is successful and contains JSON
    if response.status_code == 200:
        try:
            response_json = response.json()
            debug_print(f"Debug: {response_json}")
            if response_json.get('topics'):
                return f"{title} - Duplicate"
        except json.JSONDecodeError:
            debug_print("Error: Received non-JSON response.")
    else:
        debug_print(f"Error: Received status code {response.status_code}")

    return title

def process_markdown(markdown_text):
    html = markdown(markdown_text)
    soup = BeautifulSoup(html, 'html.parser')

    # Find the first header
    header = soup.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    title = header.get_text().strip() if header else "No Title Found"

    # Remove the first header from the soup object
    if header:
        header.extract()

    # The remaining content will be the Discourse topic content
    content = str(soup).strip()

    return title, content

def get_tag_id(tag_name):
    url = f'{DISCOURSE_URL}/tags.json'
    headers = {'Api-Key': DISCOURSE_API_KEY, 'Api-Username': DISCOURSE_API_USERNAME}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        tags = response.json().get('tags', [])
        for tag in tags:
            if tag.get('name') == tag_name:
                return tag.get('id')
    
    return None

def post_to_discourse(title, content, category_id):
    import_tag_id = get_tag_id('import')
    if import_tag_id is None:
        debug_print("Tag 'import' not found. Continuing without tagging.")
        tags_data = []
    else:
        debug_print("Tag 'import' found. Adding to topic.")
        tags_data = [import_tag_id]

    url = f'{DISCOURSE_URL}/posts.json'
    headers = {'Api-Key': DISCOURSE_API_KEY, 'Api-Username': DISCOURSE_API_USERNAME}
    data = {
        'title': title,
        'raw': content,
        'category': category_id,
        'tags_ids': ["import"]
    }
    debug_print(f"Connecting to: {url}")
    response = requests.post(url, headers=headers, data=data)
    debug_print(f"Debug: {response.json()}")
    return response.json()

def import_markdown_file(file_path, category_id):
    with open(file_path, 'r') as file:
        markdown_text = file.read()
        title, content = process_markdown(markdown_text)
        title = check_duplicate_topic(title, category_id)
        print(f'Importing "{title}"...')
        response = post_to_discourse(title, content, category_id)

def import_markdown_files(directory, category_id):
    for filename in os.listdir(directory):
        if filename.endswith('.md'):
            file_path = os.path.join(directory, filename)
            import_markdown_file(file_path, category_id)

def list_categories():
    url = f'{DISCOURSE_URL}/site.json'
    headers = {'Api-Key': DISCOURSE_API_KEY, 'Api-Username': DISCOURSE_API_USERNAME}
    debug_print(f"Connecting to: {url}")
    response = requests.get(url, headers=headers)
    debug_print(f"Debug: {response.json()}")

    categories_data = response.json().get('categories', [])
    # Create a dictionary to easily access categories by their ID
    categories_dict = {category['id']: category for category in categories_data}

    for category in categories_data:
        parent_id = category.get('parent_category_id')
        if parent_id is None:
            print_category(category)
            # Find and print subcategories
            for subcategory in categories_data:
                if subcategory.get('parent_category_id') == category['id']:
                    print_category(subcategory, indent="  - ")

def print_category(category, indent=""):
    print(f"{indent}{category['id']}: {category['name']}")

def test_connection():
    url = f'{DISCOURSE_URL}/site.json'
    headers = {'Api-Key': DISCOURSE_API_KEY, 'Api-Username': DISCOURSE_API_USERNAME}
    debug_print(f"Connecting to: {url}")
    try:
        response = requests.get(url, headers=headers)
        debug_print(f"Debug: {response.json()}")
        if response.status_code == 200:
            print("Connection successful.")
        else:
            print(f"Connection failed with status code {response.status_code}.")
    except requests.RequestException as e:
        print(f"Connection failed: {e}")
        
# Function to preview markdown file processing
def preview_markdown_file(file_path):
    with open(file_path, 'r') as file:
        markdown_text = file.read()
        title, content = process_markdown(markdown_text)
        print(f"Previewing '{file_path}':")
        print("Discourse Topic Title:")
        print(title)
        print("\nDiscourse Topic Content:")
        print(content)
        
# Main functionality
if args.preview:
    preview_markdown_file(args.preview)
elif args.list_categories:
    list_categories()
elif args.test_connection:
    test_connection()
elif CATEGORY_ID and args.file:
    import_markdown_file(args.file, CATEGORY_ID)
elif CATEGORY_ID and args.directory:
    import_markdown_files(args.directory, CATEGORY_ID)
else:
    parser.print_help()
