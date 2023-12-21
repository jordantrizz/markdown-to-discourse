#!/usr/bin/python3
import os
import requests
import markdown
import json
import argparse

# Argument Parser Setup
parser = argparse.ArgumentParser(description='Import Markdown files into Discourse')
parser.add_argument('-c', '--category', type=int, required=True, help='Category ID for the Discourse posts')
parser.add_argument('-d', '--directory', type=str, required=True, help='Directory containing Markdown files')
args = parser.parse_args()

# Load configuration from JSON file
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

DISCOURSE_API_KEY = config['discourse_api_key']
DISCOURSE_API_USERNAME = config['discourse_api_username']
DISCOURSE_URL = config['discourse_url']
CATEGORY_ID = args.category  # Category ID from command line argument

def get_first_header(markdown_text):
    md = markdown.Markdown(extensions=['meta'])
    md.convert(markdown_text)
    for token in md.parser.tokens:
        if token['type'] == 'heading' and token['level'] == 1:
            return token['children'][0]['raw_text']
    return None

def post_to_discourse(title, content):
    headers = {'Api-Key': DISCOURSE_API_KEY, 'Api-Username': DISCOURSE_API_USERNAME}
    data = {
        'title': title,
        'raw': content,
        'category': CATEGORY_ID
    }
    response = requests.post(f'{DISCOURSE_URL}/posts.json', headers=headers, data=data)
    return response.json()

def import_markdown_files(directory):
    for filename in os.listdir(directory):
        if filename.endswith('.md'):
            with open(os.path.join(directory, filename), 'r') as file:
                content = file.read()
                title = get_first_header(content)
                if title:
                    print(f'Importing "{title}"...')
                    response = post_to_discourse(title, content)
                    print('Response:', response)

# Running the script with command line arguments
import_markdown_files(args.directory)
