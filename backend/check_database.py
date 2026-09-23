from app.dataset.storage import get_connection

c = get_connection()

print("========================================")
print("EXPERIMENTS TABLE")
print("========================================")

experiment_table = c.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name='experiments'"
).fetchone()

print(experiment_table)

print()
print("========================================")
print("POSITIONS COLUMNS")
print("========================================")

for row in c.execute("PRAGMA table_info(positions)").fetchall():
    print(dict(row))

print()
print("========================================")
print("SAMPLES COLUMNS")
print("========================================")

for row in c.execute("PRAGMA table_info(samples)").fetchall():
    print(dict(row))

print()
print("========================================")
print("DONE")
print("========================================")

c.close()
