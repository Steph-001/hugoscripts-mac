#!/usr/bin/env python3
import json
import os
import sys

FILE_PATH = "static/data/irregular-verbs.json"

def show_help():
    help_text = """
add-verbs.py - Add irregular verbs to JSON data file

USAGE:
    add-verbs
    add-verbs [OPTIONS]

OPTIONS:
    -h, --help      Show this help message

DESCRIPTION:
    Interactive script to add English irregular verbs to a JSON data file.
    The script will:
    
    1. Load existing verbs from static/data/irregular-verbs.json
    2. Prompt you to add new irregular verb forms:
       - Base form: The infinitive (e.g., "go")
       - Past tense: Simple past (e.g., "went")
       - Past participle: Past participle (e.g., "gone")
    3. Save all verbs back to the JSON file
    
    Press Enter on a blank base form to finish adding verbs.

EXAMPLES:
    add-verbs           Add new irregular verbs
    add-verbs --help    Show this help message

JSON FORMAT:
    The script maintains a JSON array with this structure:
    
    [
      {
        "base": "go",
        "past": "went",
        "participle": "gone"
      }
    ]

NOTES:
    - Must be run from the project root directory
    - Creates static/data/irregular-verbs.json if it doesn't exist
    - Appends new entries to existing verbs
"""
    print(help_text)
    sys.exit(0)

def load_verbs():
    if os.path.exists(FILE_PATH):
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_verbs(verbs):
    # Ensure directory exists
    os.makedirs(os.path.dirname(FILE_PATH), exist_ok=True)
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(verbs, f, indent=2, ensure_ascii=False)

def main():
    # Check for help flag
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        show_help()
    
    verbs = load_verbs()
    print("Enter irregular verbs (leave base form empty to stop):\n")
    
    while True:
        base = input("Base form: ").strip()
        if not base:
            break
        past = input("Past tense: ").strip()
        participle = input("Past participle: ").strip()
        
        verbs.append({
            "base": base,
            "past": past,
            "participle": participle
        })
        print(f"✔ Added: {base} – {past} – {participle}\n")
    
    save_verbs(verbs)
    print(f"\n✅ {len(verbs)} total verbs saved to {FILE_PATH}")

if __name__ == "__main__":
    main()
