import requests
from BeautifulSoup import BeautifulSoup
import sqlite3

TICKET_URL = 'http://www.tickets.london2012.com/'
GET_VARS = {
    'form': 'search',
    'tab': 'oly',
    'sport': '',
    'venue': 'loc_1',  # Olympic park
    'fromDate': '',
    'toDate': '',
    'morning': '1',
    'afternoon': '1',
    'evening': '1',
    'show_available_events': '1',  # Only show available events
}


def send_alert(event_datetime, event_url, event_type):
    message = "Whoop! A %s event at %s just became available! Go look at %s" % (event_type, event_datetime, event_url)
    print message


def search_events():
    conn = sqlite3.connect('events.db')
    cur = conn.cursor()

    get_var_list = ['%s=%s' % (key, value) for key, value in GET_VARS.items()]
    get_str = '&'.join(get_var_list)
    search_page = requests.get('%sbrowse?%s' % (TICKET_URL, get_str)).content
    soup = BeautifulSoup(search_page)

    search_table = soup.find('tbody')
    search_rows = search_table.findAll('tr')

    search_events = {}
    for row in search_rows[::2]:  # Get every other row, excludes dividers
        event_datetime = row.find('td', attrs={'headers': 'date_time'}).find('a').string
        event_url = '%seventdetails?id=%s' % (TICKET_URL, row.find('td', attrs={'headers': 'select'}).find('input', attrs={'name': 'id'})['value'])
        event_type = row.find('td', attrs={'headers': 'sports'}).find('a').string

        session_meta = str(row.find('td', attrs={'headers': 'session'}))
        # Grab session code
        event_code = session_meta.split('Session Code:')[1].split()[0]
        search_events[event_code] = (event_datetime, event_url, event_type)

    test_events = {
        'AB123': ('Blah', '09 Tralal 2012', ''),
        'XY987': ('Rah', '12 Trololo 2012', ''),
        'ZZ567': ('Blergh', 'Some time 2012', ''),
    }
    #search_events = test_events

    recorded_events = cur.execute("SELECT * FROM events").fetchall()

    prev_in_search = [event_code for event_code, in_search in recorded_events if in_search == 1]
    prev_not_search = [event_code for event_code, in_search in recorded_events if in_search == 0]
    # "SELECT * FROM events WHERE event_code='%s'" % event_code

    # New events
    for event_code in search_events:
        if event_code not in [recorded_event_code for recorded_event_code, in_search in recorded_events]:
            send_alert(*search_events[event_code])
            cur.execute("INSERT INTO events VALUES ('%s', 1)" % event_code)
            # new_events.append(event_code)

    # Events that weren't in the previous search
    for event_code in prev_not_search:
        if event_code in search_events.keys():
            send_alert(*search_events[event_code])
            cur.execute("UPDATE events SET in_search=1 WHERE event_code='%s'" % event_code)

    # Events that are no longer listed in the search
    for event_code in prev_in_search:
        if event_code not in search_events.keys():
            cur.execute("UPDATE events SET in_search=0 WHERE event_code='%s'" % event_code)

    conn.commit()
    cur.close()

if __name__ == '__main__':
    search_events()
