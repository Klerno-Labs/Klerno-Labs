import sqlite3

conn = sqlite3.connect('data/klerno.db')
cursor = conn.cursor()

# Check what tables exist
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tables:', tables)

# Check subscription_tiers table if it exists
if ('subscription_tiers',) in tables:
    cursor.execute('PRAGMA table_info(subscription_tiers)')
    columns = cursor.fetchall()
    print('Columns in subscription_tiers:', columns)
    
    cursor.execute('SELECT * FROM subscription_tiers')
    rows = cursor.fetchall()
    print('Data in subscription_tiers:', rows)

conn.close()