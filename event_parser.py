#!/usr/bin/env python3
"""
EVENT PARSER FOR PENSA MENSA NEWSLETTER
Parses raw event text and updates JSON file with structured event data
Usage: python event_parser.py raw_text_file.txt json_file.json
"""

import re
import json
import sys
import os
from datetime import datetime
import html

class EventParser:
    def __init__(self):
        self.months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        self.current_year = datetime.now().year
        
    def clean_text(self, text):
        """Clean HTML entities and formatting"""
        text = html.unescape(text)
        text = text.replace('&#39;', "'")
        text = text.replace('&amp;', '&')
        text = text.replace('&nbsp;', ' ')
        text = text.replace('\r\n', '\n')
        text = text.replace('\r', '\n')
        return text
    
    def parse_date(self, date_str, year=None):
        """Parse date string like 'October 15' into YYYY-MM-DD"""
        if year is None:
            year = self.current_year
            
        date_str = date_str.strip()
        
        # Try different date patterns
        patterns = [
            r'(\w+)\s+(\d{1,2})',  # "October 15"
            r'(\w+)\s+(\d{1,2})(?:st|nd|rd|th)',  # "October 15th"
            r'(\d{1,2})/(\d{1,2})',  # "10/15"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_str, re.IGNORECASE)
            if match:
                if '/' in date_str:
                    month = int(match.group(1))
                    day = int(match.group(2))
                else:
                    month_name = match.group(1).lower()
                    if month_name in self.months:
                        month = self.months[month_name]
                        day = int(match.group(2))
                    else:
                        continue
                        
                return f"{year:04d}-{month:02d}-{day:02d}"
        
        return None
    
    def extract_time(self, text):
        """Extract time from text"""
        patterns = [
            r'(\d{1,2}:\d{2}\s*[ap]\.?m\.?)',  # "11:30am" or "11:30 a.m."
            r'(\d{1,2}\s*[ap]\.?m\.?)',  # "11am" or "5 p.m."
            r'at\s+(\d{1,2}:\d{2})',  # "at 11:30"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                time_str = match.group(1).replace('.', '').replace(' ', '')
                # Standardize format
                if ':' not in time_str:
                    # Add :00 if no minutes
                    if 'am' in time_str.lower():
                        time_str = time_str.lower().replace('am', ':00am')
                    elif 'pm' in time_str.lower():
                        time_str = time_str.lower().replace('pm', ':00pm')
                return time_str.lower()
        
        return "Time not found"  # need to know if we don't find it
    
    def extract_phone(self, text):
        """Extract phone number and standardize to (###) ###-#### format"""
        patterns = [
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # (555) 123-4567
            r'\d{3}/\d{3}-\d{4}',  # 555/123-4567
            r'\d{3}-\d{3}-\d{4}',  # 555-123-4567
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                phone = match.group(0).strip()
                # Extract just the digits
                digits = re.sub(r'\D', '', phone)
                if len(digits) == 10:
                    # Format as (###) ###-####
                    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                return phone

        return None
    
    def extract_url(self, text, return_original=False):
        """Extract URL and ensure it uses https://

        Args:
            text: Text to extract URL from
            return_original: If True, return (original_url, converted_url) tuple

        Returns:
            If return_original=False: converted URL string or None
            If return_original=True: (original_url, converted_url) tuple or (None, None)
        """
        # Remove trailing punctuation
        text = text.rstrip('.,;:')

        patterns = [
            r'https?://[^\s,;)]+',  # Full URL
            r'www\.[^\s,;)]+',  # www URL
            r'[a-zA-Z0-9\-]+\.(com|org|net|edu)[^\s,;)]*',  # Domain only
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                original_url = match.group(0).rstrip('.,;:')
                # Don't return email domains
                if '@' not in text[:match.start()]:
                    # Convert http:// to https://
                    converted_url = original_url
                    if original_url.startswith('http://'):
                        converted_url = 'https://' + original_url[7:]
                    # Add https:// if no protocol specified
                    elif not original_url.startswith('https://'):
                        converted_url = 'https://' + original_url

                    if return_original:
                        return (original_url, converted_url)
                    return converted_url

        if return_original:
            return (None, None)
        return None
    
    def parse_wednesday_lunchers(self, text, year):
        """Parse Wednesday Lunchers section"""
        events = {}
        
        # Find the Wednesday Lunchers section
        lunchers_start = text.find('Wednesday Lunchers')
        if lunchers_start == -1:
            return events
        
        # Get section until next major section
        lunchers_section = text[lunchers_start:]
        next_section = re.search(r'\n(In addition to our Wednesday Lunches|Panama City Ms|Pensacola Ms|Our longest running|In a change)', lunchers_section)
        if next_section:
            lunchers_section = lunchers_section[:next_section.start()]
        
        # Extract the lunchers event time for lunch events
        lunchers_time = self.extract_time(lunchers_section)

        # Parse individual lunch events
        lines = lunchers_section.split('\n')
        for line in lines:
            # Look for date patterns
            date_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}:', 
                                  line, re.IGNORECASE)
            if date_match:
                date_str = date_match.group(0).rstrip(':')
                parsed_date = self.parse_date(date_str, year)
                
                if parsed_date:
                    # Extract restaurant info
                    rest_of_line = line[date_match.end():].strip()
                    
                    # Parse restaurant name (before first comma or period)
                    name_match = re.match(r'([^,\.]+)', rest_of_line)
                    name = name_match.group(1).strip() if name_match else "Restaurant"
                    
                    # Extract location (everything after name, before phone/URL)
                    location = ""
                    remaining = rest_of_line[len(name):] if name_match else rest_of_line
                    
                    # Remove phone and URL to get clean location
                    phone = self.extract_phone(remaining)
                    url = self.extract_url(remaining)
                    
                    # Clean location
                    location_text = remaining
                    if phone:
                        location_text = location_text.replace(phone, '')
                    if url:
                        location_text = location_text.replace(url, '')
                    
                    # Get address parts
                    location_parts = [p.strip() for p in location_text.split(',')]
                    location = ', '.join([p for p in location_parts[:2] if p and not p.startswith('http')])

                    # Strip periods and spaces preceding the first alphanumeric character
                    location = re.sub(r'^[\s.]+', '', location)
                    
                    # Store event
                    if parsed_date not in events:
                        events[parsed_date] = []
                    
                    event = {
                        "time": lunchers_time,
                        "title": "Wednesday Lunchers",
                        "name": name
                    }
                    
                    if location:
                        event["location"] = location
                    if phone:
                        event["phone"] = phone
                    if url:
                        event["url"] = url
                    
                    events[parsed_date].append(event)
        
        return events
    
    def parse_happy_hour(self, text, year):
        """Parse Happy Hour section"""
        events = {}
        
        happy_start = text.find('In addition to our Wednesday Lunches')
        if happy_start == -1:
            return events
        
        happy_section = text[happy_start:]
        next_section = re.search(r'\n(Panama City Ms|Pensacola Ms|Our longest running|In a change)', happy_section)
        if next_section:
            happy_section = happy_section[:next_section.start()]
        
        happy_time = self.extract_time(happy_section)
        
        lines = happy_section.split('\n')
        for line in lines:
            date_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}:', 
                                  line, re.IGNORECASE)
            if date_match:
                date_str = date_match.group(0).rstrip(':')
                parsed_date = self.parse_date(date_str, year)
                
                if parsed_date:
                    rest_of_line = line[date_match.end():].strip()
                    
                    # Extract URL and phone first
                    original_url, url = self.extract_url(rest_of_line, return_original=True)
                    phone = self.extract_phone(rest_of_line)

                    # Remove URL and phone from rest_of_line before parsing (use original URL for removal)
                    clean_line = rest_of_line
                    if original_url:
                        clean_line = clean_line.replace(original_url, '')
                    if phone:
                        clean_line = clean_line.replace(phone, '')

                    # Parse location name
                    name = clean_line.split(',')[0].strip()

                    # Remove parentheticals with more than 2 words
                    if '(' in name and ')' in name:
                        paren_start = name.find('(')
                        paren_end = name.find(')')
                        paren_content = name[paren_start+1:paren_end]
                        if len(paren_content.split()) <= 2:
                            # Keep short parentheticals like "(downstairs)"
                            pass
                        else:
                            name = name[:paren_start].strip()

                    # Get location (everything after name)
                    location_parts = clean_line.split(',')[1:]
                    location = ', '.join(location_parts).strip() if location_parts else ""

                    # Stop at zip code (5 digits followed by space or comma or end)
                    zip_match = re.search(r'\b\d{5}\b', location)
                    if zip_match:
                        location = location[:zip_match.end()].strip()

                    # Clean up: remove trailing periods, commas, spaces; normalize spacing
                    location = location.strip().rstrip('.,').strip()
                    location = re.sub(r',\s{2,}', ', ', location)  # Multiple spaces after comma -> single space
                    location = re.sub(r',\s*[.,]*\s*$', '', location)  # Remove trailing comma/period with spaces

                    if parsed_date not in events:
                        events[parsed_date] = []
                    
                    event = {
                        "time": happy_time,
                        "title": "Happy Hour",
                        "name": name,
                    }
                    
                    if location:
                        event["location"] = location
                    if phone:
                        event["phone"] = phone
                    if url:
                        event["url"] = url
                    
                    events[parsed_date].append(event)
        
        return events
    
    def parse_other_events(self, text, year):
        """Parse Panama City, Pensacola, Cheers events"""
        events = {}
        date_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}'
        
        # Panama City
        if 'Panama City Ms' in text:
            # Look for dates like "October 4 and November 1"
            pc_start = text.find('Panama City Ms')
        
        if pc_start == -1:
            return events

        pc_section = text[pc_start:]
        next_section = re.search(r'\n(Pensacola Ms|Our longest running|In a change)', pc_section)
        if next_section:
            pc_section = pc_section[:next_section.start()]
            
            time = self.extract_time(pc_section)
            url = self.extract_url(pc_section)
            phone = self.extract_phone(pc_section)
            name = "Newk's Eatery" # Need to make this smarter
            location = "676 West 23rd Street, Panama City" # Need to make this smarter
            
            for match in re.finditer(date_pattern, pc_section[:500], re.IGNORECASE):  # Limit search
                parsed_date = self.parse_date(match.group(0), year)
                if parsed_date:
                    if parsed_date not in events:
                        events[parsed_date] = []
                    
                    event = {
                        "time": time,
                        "title": "Panama City Lunch",
                        "name": name,
                    }
                    
                    if location:
                        event["location"] = location
                    if phone:
                        event["phone"] = phone
                    if url:
                        event["url"] = url
                    
                    events[parsed_date].append(event)
        
        # Pensacola
        if 'Pensacola Ms' in text:
            pen_start = text.find('Pensacola Ms')
        
        if pen_start == -1:
            return events

        pen_section = text[pen_start:]
        next_section = re.search(r'\n(Our longest running|In a change)', pen_section)
        if next_section:
            pen_section = pen_section[:next_section.start()]

            time = self.extract_time(pen_section)
            url = self.extract_url(pen_section)
            phone = self.extract_phone(pen_section)
            name = "Wine Bar inside Wine World" # Need to make this smarter
            location = "4970 Bayou Blvd, Pensacola" # Need to make this smarter
            
            for match in re.finditer(date_pattern, pen_section[:500], re.IGNORECASE):
                parsed_date = self.parse_date(match.group(0), year)
                if parsed_date:
                    if parsed_date not in events:
                        events[parsed_date] = []
                        
                    event = {
                        "time": time,
                        "title": "Pensacola Group",
                        "name": name,
                    }
                    
                    if location:
                        event["location"] = location
                    if phone:
                        event["phone"] = phone
                    if url:
                        event["url"] = url
                    
                    events[parsed_date].append(event)                                        
        
        # Cheers
        if 'Our longest running' in text:
            cheers_start = text.find('Our longest running')

        if cheers_start == -1:
            return events

        cheers_section = text[cheers_start:]

        time = self.extract_time(cheers_section)
        url = self.extract_url(cheers_section)
        phone = self.extract_phone(cheers_section)
        name = "Cheers Pub Shalimar" # Need to make this smarter
        location = "1270 N. Eglin Pkwy, Shalimar" # Need to make this smarter

        for match in re.finditer(date_pattern, cheers_section[:500], re.IGNORECASE):
            parsed_date = self.parse_date(match.group(0), year)
            if parsed_date:
                if parsed_date not in events:
                    events[parsed_date] = []
                    
                event = {
                    "time": time,
                    "title": "Cheers Pub",
                    "name": name,
                }
                    
                if location:
                    event["location"] = location
                if phone:
                    event["phone"] = phone
                if url:
                    event["url"] = url
                    
                events[parsed_date].append(event)                                     
        
        return events
    
    def parse_excomm(self, text, year):
        """Parse ExComm meeting"""
        events = {}
        
        if 'In a change' in text:
            excomm_section = text[text.find('In a change'):]
            
            url = self.extract_url(excomm_section)
            phone = self.extract_phone(excomm_section)
            
            # Look for date pattern
            date_match = re.search(r'(Friday|Saturday|Sunday)\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}', 
                                  excomm_section[:500], re.IGNORECASE)
            if date_match:
                # Skip day of week
                date_parts = date_match.group(0).split()
                date_str = ' '.join(date_parts[1:])  # Skip "Saturday"
                parsed_date = self.parse_date(date_str, year)
                
                if parsed_date:
                    # Extract time
                    time = self.extract_time(excomm_section[:200])
                    
                    # Extract location
                    location_match = re.search(r'Hour at\s+([^,]+),\s+([^.]+)', excomm_section[:300])
                    if location_match:
                        restaurant = location_match.group(1).strip()
                        address = location_match.group(2).strip()

                        # Clean address: remove phone and url
                        if phone:
                            address = address.replace(phone, '')
                        if url:
                            address = address.replace(url, '')

                        # Stop at zip code (5 digits)
                        zip_match = re.search(r'\b\d{5}\b', address)
                        if zip_match:
                            address = address[:zip_match.end()].strip()

                        # Normalize spacing after commas (multiple spaces -> single space)
                        address = re.sub(r',\s{2,}', ', ', address)
                        address = address.strip().strip(',').strip()
                    else:
                        restaurant = "Restaurant Not Found"
                        address = "Address Not Found"
                    
                    if parsed_date not in events:
                        events[parsed_date] = []
                    
                    events[parsed_date].append({
                        "time": time,
                        "title": "ExComm Meeting",
                        "name": restaurant,
                        "location": address,
                        "url": url,
                        "phone": phone
                    })
        
        return events
    
    def normalize_urls_in_text(self, text):
        """Normalize all URLs in text to use https://"""
        if not text:
            return text

        # First, replace all http:// URLs with https://
        text = re.sub(r'\bhttp://', 'https://', text)

        # Add https:// to www. URLs not already part of a full URL
        # Match www. that is NOT preceded by :// (to avoid matching https://www.)
        text = re.sub(r'(?<!://)\b(www\.[^\s,;)]+)', r'https://\1', text)

        # Add https:// to bare domain URLs (domain.com) NOT in email addresses or after www.
        # Match domain.ext but NOT when preceded by @ (email), :// (URL), or www. (already handled)
        # Negative lookbehind for @ and for www.
        text = re.sub(r'(?<!@)(?<!www\.)(?<!://)\b([a-zA-Z0-9\-]+\.(com|org|net|edu)(?:/[^\s,;)]*)?)(?=[\s,;)\.]|$)', r'https://\1', text)

        return text

    def extract_raw_sections(self, text):
        """Extract raw text for each event section"""
        sections = {}

        # Define section markers
        markers = [
            ('wednesday_lunchers', 'Wednesday Lunchers', ['In addition to our Wednesday Lunches', 'Panama City Ms', 'Pensacola Ms', 'Our longest running', 'In a change', '\n\n\n', None]),
            ('happy_hour', 'In addition to our Wednesday Lunches', ['Panama City Ms', 'Pensacola Ms', 'Our longest running', 'In a change', '\n\n\n', None]),
            ('panama_city', 'Panama City Ms', ['Pensacola Ms', 'Our longest running', 'In a change', None]),
            ('pensacola', 'Pensacola Ms', ['Our longest running', 'In a change', '\n\n\n', None]),
            ('cheers', 'Our longest running', ['In a change', '\n\n\n', ]),
            ('excomm', 'In a change', ['\n\n\n', None])
        ]

        for key, start_marker, end_markers in markers:
            if start_marker in text:
                start = text.find(start_marker)
                section = text[start:]

                # Find the end of section
                end_pos = len(section)
                for end_marker in end_markers:
                    if end_marker and end_marker in section:
                        pos = section.find(end_marker)
                        if pos > 0 and pos < end_pos:
                            end_pos = pos

                # Normalize URLs in the section before storing
                sections[key] = self.normalize_urls_in_text(section[:end_pos].strip())

        return sections
    
    def parse_all(self, raw_text, year=None):
        """Parse all events from raw text"""
        if year is None:
            year = self.current_year
        
        raw_text = self.clean_text(raw_text)
        all_events = {}
        
        # Parse each section
        wednesday = self.parse_wednesday_lunchers(raw_text, year)
        happy = self.parse_happy_hour(raw_text, year)
        other = self.parse_other_events(raw_text, year)
        excomm = self.parse_excomm(raw_text, year)
        
        # Merge all events
        for events_dict in [wednesday, happy, other, excomm]:
            for date, events in events_dict.items():
                if date not in all_events:
                    all_events[date] = []
                all_events[date].extend(events)
        
        # Extract raw sections
        raw_sections = self.extract_raw_sections(raw_text)
        
        return all_events, raw_sections
    
    def update_json_file(self, json_file, raw_text_file):
        """Update JSON file with parsed events"""
        
        # Load existing JSON
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Read raw text
        with open(raw_text_file, 'r', encoding='utf-8') as f:
            raw_text = f.read()
        
        # Determine year from config
        year_match = re.search(r'(\d{4})', data['config']['month_year'])
        year = int(year_match.group(1)) if year_match else datetime.now().year
        
        # Parse events and raw sections
        events, raw_sections = self.parse_all(raw_text, year)
        
        # Update events in JSON
        data['events'] = events
        
        # Update raw text sections if they exist
        if 'static_content' in data and 'event_sections' in data['static_content']:
            sections = data['static_content']['event_sections']
            
            if 'wednesday_lunchers' in raw_sections:
                sections['wednesday_lunchers']['content'] = raw_sections['wednesday_lunchers']
            if 'happy_hour' in raw_sections:
                sections['happy_hour']['content'] = raw_sections['happy_hour']
            if 'panama_city' in raw_sections:
                sections['panama_city']['content'] = raw_sections['panama_city']
            if 'pensacola' in raw_sections:
                sections['pensacola']['content'] = raw_sections['pensacola']
            if 'cheers' in raw_sections:
                sections['cheers']['content'] = raw_sections['cheers']
            if 'excomm' in raw_sections:
                sections['excomm']['content'] = raw_sections['excomm']
        
        # Save updated JSON
        output_file = json_file.replace('.json', '_updated.json')
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=4)
        
        print(f"✅ Updated JSON saved to: {output_file}")
        print(f"📊 Parsed {len(events)} event dates")
        print(f"📝 Total {sum(len(e) for e in events.values())} individual events")
        
        # Display summary
        print("\n📅 Events Summary:")
        for date in sorted(events.keys()):
            print(f"  {date}:")
            for event in events[date]:
                print(f"    - {event['time']}: {event['title']} at {event['name']}")

        
        return output_file

def main():
    """Main entry point"""
    if len(sys.argv) < 3:
        print("❌ Error: Missing arguments")
        print("\nUsage: python event_parser.py raw_text_file.txt json_file.json")
        print("\nExample: python event_parser.py events_raw.txt pensa_mensa_content.json")
        print("\nThis will create a new file: pensa_mensa_content_updated.json")
        sys.exit(1)
    
    raw_text_file = sys.argv[1]
    json_file = sys.argv[2]
    
    if not os.path.exists(raw_text_file):
        print(f"❌ Error: Raw text file '{raw_text_file}' not found")
        sys.exit(1)
    
    if not os.path.exists(json_file):
        print(f"❌ Error: JSON file '{json_file}' not found")
        sys.exit(1)
    
    parser = EventParser()
    
    try:
        updated_file = parser.update_json_file(json_file, raw_text_file)
        print(f"\n✅ Success! You can now generate the newsletter with:")
        print(f"   python final_generator.py {updated_file} newsletter.pdf")
        
    except Exception as e:
        print(f"❌ Error parsing events: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()