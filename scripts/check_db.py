import sqlite3
conn = sqlite3.connect('services/chat_history.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('Tables:', cur.fetchall())
try:
    cur.execute("SELECT COUNT(*) FROM documents")
    print('Documents count:', cur.fetchone()[0])
except:
    print('documents table not found')
conn.close()
