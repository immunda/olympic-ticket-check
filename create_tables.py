import sqlite3

conn = sqlite3.connect('events.db')
cur = conn.cursor()
cur.execute('''CREATE TABLE events
             (event_code TEXT, in_search INT, UNIQUE(event_code))''')
