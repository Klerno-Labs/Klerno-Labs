import sqlite3

conn = sqlite3.connect('data/klerno.db')
cursor = conn.cursor()

# Update Professional tier pricing
cursor.execute('UPDATE subscription_tiers SET price_xrp = 25.0 WHERE id = "professional"')
conn.commit()

# Verify the update
cursor.execute('SELECT id, name, price_xrp FROM subscription_tiers')
tiers = cursor.fetchall()
print('Updated tiers:')
for tier in tiers:
    print(f'  {tier[0]}: {tier[1]} - {tier[2]} XRP')

conn.close()
print('Professional tier pricing updated to 25.0 XRP')