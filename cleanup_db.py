import sqlite3

conn = sqlite3.connect('data/klerno.db')
cursor = conn.cursor()

# Remove old tier entries
old_tiers = ['basic', 'premium', 'enterprise']
for tier_id in old_tiers:
    cursor.execute('DELETE FROM subscription_tiers WHERE id = ?', (tier_id,))
    print(f'Removed old tier: {tier_id}')

# Update any subscriptions that might reference old tiers
cursor.execute('UPDATE subscriptions SET tier = "starter" WHERE tier = "basic"')
cursor.execute('UPDATE subscriptions SET tier = "professional" WHERE tier = "premium"')
cursor.execute('UPDATE subscriptions SET tier = "enterprise" WHERE tier IN ("enterprise")')

conn.commit()

# Verify cleanup
cursor.execute('SELECT id, name FROM subscription_tiers')
remaining_tiers = cursor.fetchall()
print('Remaining tiers:', remaining_tiers)

conn.close()
print('Database cleanup complete!')