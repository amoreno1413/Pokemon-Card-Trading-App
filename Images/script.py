import sqlite3

conn = sqlite3.connect('data - Copy.db')
curr = conn.cursor()

query = 'SELECT Name, Type FROM Cards'
results = curr.execute(query).fetchall()

for result in results:
    if 'EX' in result[0] and '(' not in result[0]:
        query = 'UPDATE Cards Set Type = "EX"' \
                'WHERE Name = ?'
        curr.execute(query, (result[0],))

conn.commit()
conn.close()