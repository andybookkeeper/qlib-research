import sqlite3

conn = sqlite3.connect('./data/qlib_trading.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

print(f'✓ {len(tables)} tables created:')
for i, table in enumerate(tables, 1):
    print(f'  {i:2}. {table[0]}')

# Show table details
cursor.execute("PRAGMA foreign_keys=on")
print('\n✓ Foreign key constraints enabled')

# Get column count per table
print('\n✓ Table schemas:')
for table in tables:
    table_name = table[0]
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    print(f'  {table_name}: {len(columns)} columns')

conn.close()
print('\n✓ Database verification complete!')
