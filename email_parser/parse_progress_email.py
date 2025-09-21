#!/usr/bin/env python3
"""
Parse progress emails to extract Daily Active Minutes and other data
"""

from bs4 import BeautifulSoup
import re
from datetime import datetime
import json


def parse_daily_active_minutes(html_content):
    """Extract Daily Active Minutes from the HTML email"""
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find the Daily Active Minutes section
    daily_minutes = {}
    days = ['S', 'M', 'T', 'W', 'T', 'F', 'S']
    day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

    # Look for the table containing the daily minutes
    # The structure has divs with minutes values followed by colored bars
    minutes_divs = []

    # Find all divs that might contain minute values
    for div in soup.find_all('div', style=lambda x: x and 'color:rgb(156,163,175)' in x):
        text = div.get_text(strip=True)
        # If it's a number or empty, it's a minute value
        if text.isdigit() or text == '':
            minutes_divs.append(int(text) if text else 0)

    # Map minutes to days
    if len(minutes_divs) >= 7:
        for i, day in enumerate(day_names):
            daily_minutes[day] = minutes_divs[i]

    return daily_minutes


def parse_games_played(html_content):
    """Extract games played information"""
    soup = BeautifulSoup(html_content, 'html.parser')
    games = []

    # Find the Games Played section first
    games_section = None
    for p in soup.find_all('p'):
        if 'Games Played' in p.get_text():
            games_section = p.find_parent('table')
            if games_section:
                games_section = games_section.find_next_sibling('table')
            break

    if not games_section:
        return games

    # Within the games section, look for game entries
    # Each game has a structure with name, category, time, and description
    for table in [games_section]:
        # Find all game entries within this section
        game_tables = table.find_all('table', recursive=True)

        current_game = {}
        for subtable in game_tables:
            # Look for game name (font-size:24px)
            game_name = subtable.find('p', style=lambda x: x and 'font-size:24px' in x)
            if game_name:
                if current_game:
                    games.append(current_game)
                current_game = {'name': game_name.get_text(strip=True)}

            # Look for category
            if current_game:
                category = subtable.find('p', style=lambda x: x and 'font-size:12px' in x and 'color:rgb(156,163,175)' in x and 'display:inline' in x)
                if category:
                    current_game['category'] = category.get_text(strip=True)

        # Now find time and description for the current game
        if current_game and 'name' in current_game:
            # Look for time in the parent structure
            for p in table.find_all('p', style=lambda x: x and 'font-weight:600' in x and 'font-size:12px' in x):
                text = p.get_text(strip=True)
                if 'minutes on' in text:
                    match = re.match(r'([\d.]+)\s+minutes?\s+on\s+(\w+)', text)
                    if match:
                        current_game['minutes'] = float(match.group(1))
                        current_game['day'] = match.group(2)

                        # Get description if available
                        next_p = p.find_next_sibling('p')
                        if next_p and 'font-style:italic' in next_p.get('style', ''):
                            current_game['description'] = next_p.get_text(strip=True)

                        games.append(current_game)
                        break

    return games


def parse_lessons_in_progress(html_content):
    """Extract lessons in progress information"""
    soup = BeautifulSoup(html_content, 'html.parser')
    lessons = []

    # Find the Lessons In Progress section
    lessons_section = None
    for p in soup.find_all('p'):
        if 'Lessons In Progress' in p.get_text():
            lessons_section = p.find_parent('table')
            break

    if lessons_section:
        # Find lesson entries within this section
        for table in lessons_section.find_next_siblings('table'):
            lesson_info = {}

            # Find lesson name
            lesson_name_p = table.find('p', style=lambda x: x and 'font-size:24px' in x)
            if lesson_name_p:
                lesson_info['name'] = lesson_name_p.get_text(strip=True)

            # Find category
            category_p = table.find('p', style=lambda x: x and 'font-size:12px' in x and 'color:rgb(156,163,175)' in x)
            if category_p:
                lesson_info['category'] = category_p.get_text(strip=True)

            # Find time spent
            for p in table.find_all('p', style=lambda x: x and 'font-weight:600' in x and 'font-size:12px' in x):
                text = p.get_text(strip=True)
                match = re.match(r'([\d.]+)\s+minutes?\s+on\s+(\w+)', text)
                if match:
                    lesson_info['minutes'] = float(match.group(1))
                    lesson_info['day'] = match.group(2)
                    break

            if 'name' in lesson_info:
                lessons.append(lesson_info)

    return lessons


def parse_email_metadata(html_content):
    """Extract email metadata like date and student name"""
    soup = BeautifulSoup(html_content, 'html.parser')
    metadata = {}

    # Find student name - it's in the h1 tag
    h1 = soup.find('h1')
    if h1:
        text = h1.get_text()
        match = re.search(r"Update on\s+(\w+)'s\s+progress", text)
        if match:
            metadata['student_name'] = match.group(1)

    # Find parent name in greeting
    for p in soup.find_all('p'):
        text = p.get_text(strip=True)
        if text.startswith('Hello'):
            match = re.match(r'Hello\s+(\w+)', text)
            if match:
                metadata['parent_name'] = match.group(1)

    return metadata


def parse_progress_email(html_content, email_date=None):
    """Parse complete progress email and return structured data"""
    result = {
        'date': email_date,
        'metadata': parse_email_metadata(html_content),
        'daily_active_minutes': parse_daily_active_minutes(html_content),
        'games_played': parse_games_played(html_content),
        'lessons_in_progress': parse_lessons_in_progress(html_content)
    }

    # Calculate total weekly minutes
    total_minutes = sum(result['daily_active_minutes'].values())
    result['total_weekly_minutes'] = total_minutes

    return result


def main():
    """Test the parser with a sample email"""
    import sys

    # Use the most recent email file
    email_file = 'email_12115.html' if len(sys.argv) < 2 else sys.argv[1]

    try:
        with open(email_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Parse the email
        result = parse_progress_email(html_content, 'Mon, 15 Sep 2025 13:20:59 +0000')

        # Print results
        print(json.dumps(result, indent=2))

        # Summary
        print("\n" + "="*50)
        print("SUMMARY")
        print("="*50)
        print(f"Student: {result['metadata'].get('student_name', 'Unknown')}")
        print(f"Parent: {result['metadata'].get('parent_name', 'Unknown')}")
        print(f"Total Weekly Minutes: {result['total_weekly_minutes']}")
        print("\nDaily Breakdown:")
        for day, minutes in result['daily_active_minutes'].items():
            if minutes > 0:
                print(f"  {day}: {minutes} minutes")

        if result['games_played']:
            print("\nGames Played:")
            for game in result['games_played']:
                print(f"  - {game.get('name', 'Unknown')}: {game.get('minutes', 0)} min on {game.get('day', 'Unknown')}")

        if result['lessons_in_progress']:
            print("\nLessons in Progress:")
            for lesson in result['lessons_in_progress']:
                print(f"  - {lesson.get('name', 'Unknown')}: {lesson.get('minutes', 0)} min on {lesson.get('day', 'Unknown')}")

    except FileNotFoundError:
        print(f"Error: {email_file} not found. Run fetch_email_content.py first.")
    except Exception as e:
        print(f"Error parsing email: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()