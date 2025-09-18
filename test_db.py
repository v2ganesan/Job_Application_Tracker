#!/usr/bin/env python3
# Simple script to test PostgreSQL connection

from src.database import test_connection, init_database

if __name__ == "__main__":
    print("🚀 Testing PostgreSQL setup...")
    
    # Test connection
    if test_connection():
        print("\n📋 Initializing database tables...")
        if init_database():
            print("\n✅ PostgreSQL setup complete!")
        else:
            print("\n❌ Failed to initialize database")
    else:
        print("\n❌ Connection failed - check your PostgreSQL setup")
        print("\nMake sure:")
        print("1. PostgreSQL is running")
        print("2. Database 'job_tracker' exists")
        print("3. Connection settings in database.py are correct")
