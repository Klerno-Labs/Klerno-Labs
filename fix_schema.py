import sqlite3

conn = sqlite3.connect('data/klerno.db')
cursor = conn.cursor()

# Check current schema
cursor.execute('PRAGMA table_info(subscription_tiers)')
columns = cursor.fetchall()
print('Current columns:', [col[1] for col in columns])

# Add missing columns if they don't exist
existing_columns = [col[1] for col in columns]

if 'transaction_limit' not in existing_columns:
    cursor.execute('ALTER TABLE subscription_tiers ADD COLUMN transaction_limit INTEGER')
    print('Added transaction_limit column')

if 'api_rate_limit' not in existing_columns:
    cursor.execute('ALTER TABLE subscription_tiers ADD COLUMN api_rate_limit INTEGER')
    print('Added api_rate_limit column')

# Update with the correct limits
updates = [
    ('starter', 1000, 100),
    ('professional', 100000, 1000),
    ('enterprise', None, None)  # Unlimited
]

for tier_id, tx_limit, api_limit in updates:
    cursor.execute(
        'UPDATE subscription_tiers SET transaction_limit = ?, api_rate_limit = ? WHERE id = ?',
        (tx_limit, api_limit, tier_id)
    )
    print(f'Updated {tier_id}: {tx_limit} transactions, {api_limit} API requests/hour')

conn.commit()

# Verify updates
cursor.execute('SELECT id, name, price_xrp, transaction_limit, api_rate_limit FROM subscription_tiers')
tiers = cursor.fetchall()
print('\nFinal tier configuration:')
for tier in tiers:
    tx_limit = 'Unlimited' if tier[3] is None else tier[3]
    api_limit = 'Unlimited' if tier[4] is None else tier[4]
    print(f'  {tier[1]}: {tier[2]} XRP, {tx_limit} tx/month, {api_limit} API/hour')

conn.close()
print('\nDatabase schema and limits updated!')