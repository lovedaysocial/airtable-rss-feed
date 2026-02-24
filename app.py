from flask import Flask, Response
import requests
from xml.etree import ElementTree as ET
from datetime import datetime
import os

app = Flask(__name__)

# Your Airtable token will be added securely in Vercel (not here)
AIRTABLE_TOKEN = os.environ.get('AIRTABLE_TOKEN')

# Your Base ID – from your Airtable URL: airtable.com/appW2SWPgF4UpXNIX/...
# Confirm it's correct; if not, change it here
BASE_ID = 'appW2SWPgF4UpXNlX'

# List of sections/tables – update these names exactly as they appear in your Airtable tabs
# For now, start with just 'Inspiration'. Add more after testing.
SOURCES = {
   'Inspiration': {'table': 'tbl7X4PErUG8qyhDz', 'view': 'API Full'},
    # Uncomment and edit these lines once the first one works:
    # 'Tutorials': {'table': 'Tutorials', 'view': None},
    # 'Templates': {'table': 'Templates', 'view': None},
    # 'Behind the Scenes': {'table': 'Behind the Scenes', 'view': None},
    # 'Courses': {'table': 'Courses', 'view': None},
    # 'Quarterly Workshops': {'table': 'Quarterly Workshops', 'view': None},
}

def fetch_records(table_name, view_name=None):
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table_name}"
    if view_name:
        url += f"?view={view_name}"
    headers = {'Authorization': f'Bearer {AIRTABLE_TOKEN}'}
    records = []
    offset = None
    while True:
        current_url = url
        if offset:
            current_url += f"&offset={offset}"
        response = requests.get(current_url, headers=headers)
        if response.status_code != 200:
            print(f"Error fetching {table_name}: {response.text}")
            return []
        data = response.json()
        records.extend(data.get('records', []))
        offset = data.get('offset')
        if not offset:
            break
    return records

@app.route('/rss-all.xml')
def rss_all():
    if not AIRTABLE_TOKEN:
        return Response("Error: Airtable token not set", status=500)

    debug_info = []  # Collect debug messages
    all_records = []

    for section, config in SOURCES.items():
        table_id_or_name = config['table']
        view_name = config['view']
        debug_info.append(f"Fetching section '{section}' from table/ID '{table_id_or_name}' (view: {view_name})")

        try:
            records = fetch_records(table_id_or_name, view_name)
            debug_info.append(f"Fetched {len(records)} records from '{table_id_or_name}'")
            for r in records:
                r['section'] = section
            all_records.extend(records)
        except Exception as e:
            debug_info.append(f"Error fetching '{table_id_or_name}': {str(e)}")

    debug_text = "\n".join(debug_info) if debug_info else "No debug info"

    rss = ET.Element('rss', {'version': '2.0'})
    channel = ET.SubElement(rss, 'channel')
    ET.SubElement(channel, 'title').text = 'Idea Engine - All Content RSS Feed (Debug Mode)'
    ET.SubElement(channel, 'link').text = 'https://airtable-rss-feed.vercel.app/rss-all.xml'
    ET.SubElement(channel, 'description').text = f"Debug info:\n{debug_text}\n\nLive combined feed from Airtable Idea Engine"

    for record in all_records:
        fields = record['fields']
        item = ET.SubElement(channel, 'item')
        section = record.get('section', 'Unknown')
        title_field = fields.get('A Idea', 'Untitled')
        ET.SubElement(item, 'title').text = f"[{section}] {title_field}"
        desc = (
            f"Why it works: {fields.get('Why it works', 'N/A')}\n"
            f"Created: {fields.get('Created', 'N/A')}"
        )
        ET.SubElement(item, 'description').text = desc
        ET.SubElement(item, 'pubDate').text = fields.get('Created', datetime.utcnow().isoformat() + 'Z')

    xml_str = ET.tostring(rss, encoding='unicode', method='xml')
    return Response(xml_str, mimetype='application/rss+xml')

if __name__ == '__main__':
    app.run(debug=True)
