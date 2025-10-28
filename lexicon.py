#!/usr/bin/env python3
import os
import re
import sys

def show_help():
    help_text = """
lexicon.py - Add vocabulary terms to Hugo markdown frontmatter

USAGE:
    lexicon <path_to_markdown_file>
    lexicon [OPTIONS]

OPTIONS:
    -h, --help      Show this help message

DESCRIPTION:
    Interactive script to add lexicon entries to a markdown file's frontmatter.
    The script will:
    
    1. Read the existing frontmatter from the markdown file
    2. Prompt you to add new lexicon entries interactively:
       - Term: The vocabulary word (use * for stress, e.g., "hé*ro")
       - Definition: The meaning of the term
    3. Create a backup of the original file (.bak)
    4. Update the file with new entries added to the lexicon section

    Stress notation:
    - If you include asterisks (*) in the term, they mark stressed syllables
    - Example: "hé*ro" becomes term="héro", stressed="hé*ro"
    - Without asterisks, term and stressed will be identical

EXAMPLES:
    lexicon content/posts/my-article.md    Add entries to my-article.md
    lexicon --help                         Show this help message

FRONTMATTER FORMAT:
    The script adds entries to a 'lexicon:' section in YAML frontmatter:
    
    ---
    title: "My Article"
    lexicon:
      - term: "bonjour"
        definition: "hello"
        stressed: "bonjour"
    ---

NOTES:
    - Original file is backed up to <filename>.bak before modification
    - Press Enter on a blank term to finish adding entries
    - The script creates the lexicon section if it doesn't exist
"""
    print(help_text)
    sys.exit(0)

def get_frontmatter_and_content(file_path):
    """Extract frontmatter and remaining content from the file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)', content, re.DOTALL)
    if not match:
        return None, content
    return match.group(1), match.group(2)

def escape_yaml_string(s):
    """Escape double quotes for YAML."""
    return s.replace('"', '\\"')

def build_entry(term, definition, stressed):
    term_esc = escape_yaml_string(term)
    def_esc = escape_yaml_string(definition)
    stressed_esc = escape_yaml_string(stressed)
    return f'  - term: "{term_esc}"\n    definition: "{def_esc}"\n    stressed: "{stressed_esc}"'

def insert_into_frontmatter(frontmatter, new_entries):
    """Insert entries under lexicon: (create if not present)."""
    if re.search(r'^\s*lexicon:\s*$', frontmatter, flags=re.MULTILINE):
        # lexicon exists but has no entries
        return re.sub(r'^\s*lexicon:\s*$', 'lexicon:\n' + "\n".join(new_entries),
                      frontmatter, count=1, flags=re.MULTILINE)
    match = re.search(r'(lexicon:\s*(?:\n(?:[ \t]+-.*?)+))', frontmatter, flags=re.DOTALL)
    if match:
        # Append to existing list
        block = match.group(1).rstrip()
        updated_block = block + "\n" + "\n".join(new_entries)
        return frontmatter[:match.start(1)] + updated_block + frontmatter[match.end(1):]
    else:
        # No lexicon section at all
        suffix = ("\n" if not frontmatter.endswith("\n") else "") + "lexicon:\n" + "\n".join(new_entries)
        return frontmatter + suffix

def add_lexicon_entries(file_path):
    frontmatter_text, remaining_content = get_frontmatter_and_content(file_path)
    if frontmatter_text is None:
        print(f"Error: Could not find frontmatter in {file_path}")
        return
    new_entries = []
    print("\nAdding new lexicon entries. Press Enter on a blank term to finish.")
    while True:
        term_input = input("\nEnter term (press Enter to finish): ").strip()
        if term_input == "":
            break
        definition = input("Enter definition: ").strip()
        if '*' in term_input:
            stressed = term_input
            term = term_input.replace('*', '')
        else:
            term = term_input
            stressed = term  # no prompt
        entry_text = build_entry(term, definition, stressed)
        new_entries.append(entry_text)
        print(f"Added: term='{term}' definition='{definition}' stressed='{stressed}'")
    if not new_entries:
        print("No entries added.")
        return
    updated_frontmatter = insert_into_frontmatter(frontmatter_text, new_entries)
    # Backup original
    backup_path = file_path + ".bak"
    with open(backup_path, 'w', encoding='utf-8') as bak:
        with open(file_path, 'r', encoding='utf-8') as orig:
            bak.write(orig.read())
    # Write updated file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(f"---\n{updated_frontmatter}\n---\n{remaining_content}")
    print(f"\nFile updated successfully. Backup saved as {backup_path}")

def main():
    # Check for help flag first
    if len(sys.argv) == 2 and sys.argv[1] in ['-h', '--help']:
        show_help()
    
    if len(sys.argv) != 2:
        print("Usage: lexicon <path_to_markdown_file>")
        print("Try 'lexicon --help' for more information.")
        sys.exit(1)
    
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)
    
    add_lexicon_entries(file_path)

if __name__ == "__main__":
    main()
