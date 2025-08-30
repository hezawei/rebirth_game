import psycopg2
from urllib.parse import urlparse
from config.settings import settings
import traceback

# This script is for testing the database connection directly using psycopg2.
# Run it from the 'rebirth_game' directory: python test_db_connection.py

def test_connection_psycopg2():
    """Attempts to connect to the database using psycopg2."""
    db_url = settings.database_url
    if not db_url:
        print("❌ Error: DATABASE_URL is not set in your .env file or settings.")
        return

    print(f"Attempting to connect using psycopg2...")
    print(f"Target: {db_url.replace(urlparse(db_url).password, '********')}")

    try:
        # Parse the DATABASE_URL
        result = urlparse(db_url)
        
        # Connect to the database
        connection = psycopg2.connect(
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port,
            dbname=result.path[1:]  # Remove the leading '/'
        )
        
        print("✅ Connection Successful!")
        
        # Create a cursor to execute SQL queries
        cursor = connection.cursor()
        
        # Example query
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        print(f"PostgreSQL Version: {db_version[0]}")

        # Close the cursor and connection
        cursor.close()
        connection.close()
        print("Connection closed.")

    except Exception as e:
        print("❌ Connection Failed.")
        print("\nFull Error Traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    test_connection_psycopg2()
