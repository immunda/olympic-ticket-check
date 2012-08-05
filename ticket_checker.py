import requests
from BeautifulSoup import BeautifulSoup
import sqlite3
import smtplib
from email.mime.text import MIMEText

from local_settings import *

IGNORE_ORBIT_EVENTS = True
SMTP_HOST = 'localhost'
#EMAIL_SENDER = ''
#EMAIL_RECIPIENTS = []
TICKET_URL = 'http://www.tickets.london2012.com/'
GET_VARS = {
    'form': 'search',
    'tab': 'oly',  # For Olympic events, use parap for Paralympic
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
    message = MIMEText("Go, go, go! A(n) %s event on %s just became available! Go look at %s" % (event_type, event_datetime, event_url), 'plain')
    message['Subject'] = 'New event available!'
    message['From'] = EMAIL_SENDER
    message['To'] = ', '.join(EMAIL_RECIPIENTS)
    server = smtplib.SMTP(SMTP_HOST)
    server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENTS, message.as_string())
    server.quit()


def get_search_page(offset=0):
    get_var_list = ['%s=%s' % (key, value) for key, value in GET_VARS.items()]
    get_str = '&'.join(get_var_list)
    search_page = requests.get('%sbrowse?%s&offset=%s' % (TICKET_URL, get_str, offset)).content
    return search_page


def search_events():
    conn = sqlite3.connect('events.db')
    cur = conn.cursor()

    search_page = get_search_page()
    soup = BeautifulSoup(search_page)

    search_table = soup.find('tbody')
    search_rows = search_table.findAll('tr')

    num_sessions_text = soup.find('div', attrs={'class': 'mgBot10 searchPagi'}).contents[2]
    num_sessions = num_sessions_text.split('sessions')[0].split()[-1]
    for offset in range(10, int(num_sessions), 10):  # Get further pages
        search_page = get_search_page(offset)
        more_soup = BeautifulSoup(search_page)
        search_table = more_soup.find('tbody')
        search_rows.extend(search_table.findAll('tr'))

    search_events = {}

    for row in search_rows:  # Get every other row, excludes dividers
        if row.find('td', attrs={'class': 'edp_chopDiv'}):  # Divider row
            continue
        try:
            event_url_id = row.find('td', attrs={'headers': 'select'}).find('input', attrs={'name': 'id'})['value']
        except TypeError:  # Caused it there's a problem getting the ID, can be if the event is not available
            continue
        event_datetime = row.find('td', attrs={'headers': 'date_time'}).find('a').string
        event_url = '%seventdetails?id=%s' % (TICKET_URL, row.find('td', attrs={'headers': 'select'}).find('input', attrs={'name': 'id'})['value'])
        event_type = row.find('td', attrs={'headers': 'sports'}).find('a').string

        session_meta = str(row.find('td', attrs={'headers': 'session'}))
        # Grab session code
        event_code = session_meta.split('Session Code:')[1].split()[0]
        if event_code.startswith('OB') and IGNORE_ORBIT_EVENTS == True:  # Ignore Orbit events if specified
            continue
        event_page = requests.get(event_url).content
        event_soup = BeautifulSoup(event_page)
        ticket_limit = event_soup.find('div', attrs={'class': 'tix_limit_num'}).string
        can_add_to_basket = event_soup.find('button', attrs={'id': 'add_to_list'})
        if int(ticket_limit) == 0 or can_add_to_basket is None:  # If there's 0 available tickets for event, ignore
            continue
        print '%s - %s' % (event_code, event_url)
        search_events[event_code] = (event_datetime, event_url, event_type)

    test_events = {
        'AB123': ('09 Tralal 2012', '', 'Blah'),
        'XY987': ('12 Trololo 2012', '', 'Rah'),
        'ZZ567': ('Some time 2012', '', 'Blergh'),
    }
    #search_events = test_events

    recorded_events = cur.execute("SELECT * FROM events").fetchall()

    prev_in_search = [event_code for event_code, in_search in recorded_events if in_search == 1]
    prev_not_search = [event_code for event_code, in_search in recorded_events if in_search == 0]

    # New events
    for event_code in search_events:
        if event_code not in [recorded_event_code for recorded_event_code, in_search in recorded_events]:
            send_alert(*search_events[event_code])
            cur.execute("INSERT INTO events VALUES ('%s', 1)" % event_code)

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
