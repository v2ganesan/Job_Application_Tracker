# Simple PostgreSQL connection for user tracking
import psycopg2
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_db_connection():
    """Get PostgreSQL database connection"""
    try:
        # PostgreSQL connection using environment variables
        connection = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "job_tracker"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD")
        )
        return connection
    except psycopg2.Error as e:
        print(f"❌ Database connection failed: {e}")
        print("Make sure your .env file has the correct database credentials")
        return None

def init_database():
    """Create users table if it doesn't exist"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    sheet_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            connection.commit()
            print("✅ Database initialized - users table ready")
            return True
    except psycopg2.Error as e:
        print(f"❌ Failed to create table: {e}")
        return False
    finally:
        connection.close()

def user_exists(user_email):
    """Check if user already exists in database"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM users WHERE email = %s", (user_email,))
            count = cursor.fetchone()[0]
            return count > 0
    except psycopg2.Error as e:
        print(f"❌ Failed to check user: {e}")
        return False
    finally:
        connection.close()

def save_new_user(user_email, sheet_id):
    """Save new user with their sheet ID"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (email, sheet_id) VALUES (%s, %s)",
                (user_email, sheet_id)
            )
            connection.commit()
            print(f"✅ Saved new user: {user_email}")
            return True
    except psycopg2.Error as e:
        print(f"❌ Failed to save user: {e}")
        return False
    finally:
        connection.close()

def get_user_sheet_id(user_email):
    """Get the sheet ID for an existing user"""
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT sheet_id FROM users WHERE email = %s", (user_email,))
            result = cursor.fetchone()
            return result[0] if result else None
    except psycopg2.Error as e:
        print(f"❌ Failed to get user sheet ID: {e}")
        return None
    finally:
        connection.close()

def update_user_sheet_id(user_email, sheet_id):
    """Update the sheet ID for an existing user"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET sheet_id = %s WHERE email = %s",
                (sheet_id, user_email)
            )
            connection.commit()
            print(f"✅ Updated sheet ID for user: {user_email}")
            return True
    except psycopg2.Error as e:
        print(f"❌ Failed to update user sheet ID: {e}")
        return False
    finally:
        connection.close()

def test_connection():
    """Test PostgreSQL connection"""
    print("🔌 Testing PostgreSQL connection...")
    connection = get_db_connection()
    if connection:
        print("✅ PostgreSQL connection successful!")
        connection.close()
        return True
    else:
        print("❌ PostgreSQL connection failed!")
        return False
