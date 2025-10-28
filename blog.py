import os
import sys
import datetime
import pytz

# Add help function
def show_help():
    help_text = """
blog.py - Create a new Hugo blog post

USAGE:
    blog [OPTIONS]

OPTIONS:
    -h, --help      Show this help message

DESCRIPTION:
    Interactive script to create a new blog post in content/news/
    The script will prompt you for:
    
    - Title: The post title (required)
    - Draft: Whether this is a draft (default: true)
    - Tags: Comma-separated list of tags
    - Categories: Comma-separated list of categories
    - Body: Post content (type 'exit' on a new line to finish)
    
    Date/time is automatically set to current Paris time.

EXAMPLES:
    blog                    Start interactive post creation
    blog --help            Show this help message

OUTPUT:
    Creates a markdown file in content/news/ with the format:
    <title-in-lowercase-with-hyphens>.md
"""
    print(help_text)
    sys.exit(0)

# Check for help flag
if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
    show_help()

# Define the path where new posts will be created
POSTS_DIR = 'content/news/'

# Function to prompt for input and handle blank values
def prompt_for_input(prompt, default=""):
    value = input(f"{prompt} [{default}]: ").strip()
    return value if value else default

# Get the current date and time in UTC (for ISO 8601 format)
current_date = datetime.datetime.now(pytz.timezone('Europe/Paris')).strftime("%Y-%m-%dT%H:%M:%S%z")

# Prompt the user for front matter
title = prompt_for_input("Enter the title of the post", "")
date = current_date  # Use the current date with timezone info
draft = prompt_for_input("Is this a draft? (true/false)", "true")
tags = prompt_for_input("Enter the tags (comma separated)", "").split(",")
categories = prompt_for_input("Enter the categories (comma separated)", "").split(",")

# Generate the front matter as a string
front_matter = f"""---
title: "{title}"
date: {date}
draft: {draft}
tags: [{', '.join([f'"{tag.strip()}"' for tag in tags])}]
categories: [{', '.join([f'"{category.strip()}"' for category in categories])}]
---
"""

# Prompt for the main body content of the post
print("\nEnter the body of the post (type 'exit' to finish):")
body = ""
while True:
    line = input()
    if line.strip().lower() == 'exit':
        break
    body += line + "\n"

# Combine the front matter and body
post_content = front_matter + "\n" + body

# Generate the file path for the new post
file_name = f"{title.lower().replace(' ', '-')}.md"
post_path = os.path.join(POSTS_DIR, file_name)

# Write the content to the new file
os.makedirs(POSTS_DIR, exist_ok=True)  # Ensure the directory exists
with open(post_path, 'w') as post_file:
    post_file.write(post_content)

print(f"\nNew post created: {post_path}")
