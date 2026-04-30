import os
import django
from django.db import connections
from django.db.utils import OperationalError

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daffy_project.settings')
django.setup()

def check_db():
    db_conn = connections['default']
    try:
        db_conn.cursor()
        print("Successfully connected to the database!")
    except OperationalError as e:
        print(f"Failed to connect to the database: {e}")

if __name__ == "__main__":
    check_db()
