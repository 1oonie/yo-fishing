import os
import sqlite3
import sys

with open("schema.sql") as f:
    schema = f.read()

if os.path.exists("data.sqlite"):
    connection = sqlite3.connect("data.sqlite")
else:
    print(
        "no such file 'data.sqlite', create one using 'touch data.sqlite'",
        file=sys.stderr,
    )
    sys.exit(1)

cursor = connection.cursor()

try:
    cursor.executescript(schema)
    connection.commit()
finally:
    cursor.close()
    connection.close()

print("executed schema successfully", file=sys.stderr)
