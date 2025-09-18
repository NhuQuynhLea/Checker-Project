#!/usr/bin/env python3
"""
Cleanup orphaned database records that don't have corresponding MinIO files
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from minio import Minio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def cleanup_orphaned_records():
    """Remove database records that don't have corresponding files in MinIO."""
    print("🧹 Cleaning up orphaned database records")
    print("=" * 50)
    
    # Database connection
    db_url = os.getenv('DATABASE_URL')
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    # MinIO connection
    endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9090')
    access_key = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
    secret_key = os.getenv('MINIO_SECRET_KEY', 'minioadmin123')
    bucket_name = os.getenv('MINIO_BUCKET_NAME', 'plagiarism')
    secure = os.getenv('MINIO_SECURE', 'false').lower() == 'true'
    
    try:
        # Connect to MinIO
        client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
        
        # Get all files in MinIO
        minio_files = set()
        for obj in client.list_objects(bucket_name, recursive=True):
            minio_files.add(obj.object_name)
        
        print(f"📂 Found {len(minio_files)} files in MinIO bucket '{bucket_name}'")
        
        # Get all reference documents from database
        from sqlalchemy import text
        result = db.execute(text("SELECT id, title, object_id FROM reference_documents ORDER BY id"))
        db_records = result.fetchall()
        
        print(f"🗄️ Found {len(db_records)} records in database")
        print("\n🔍 Checking for orphaned records:")
        
        orphaned_records = []
        for record in db_records:
            record_id, title, object_id = record
            if object_id not in minio_files:
                orphaned_records.append(record)
                print(f"❌ ID {record_id}: '{title}' -> {object_id} (MISSING in MinIO)")
            else:
                print(f"✅ ID {record_id}: '{title}' -> {object_id}")
        
        if orphaned_records:
            print(f"\n🗑️ Found {len(orphaned_records)} orphaned records")
            response = input("Do you want to delete these orphaned records? (y/N): ")
            
            if response.lower() == 'y':
                for record in orphaned_records:
                    record_id, title, object_id = record
                    from sqlalchemy import text
                    db.execute(text("DELETE FROM reference_documents WHERE id = :id"), {"id": record_id})
                    print(f"🗑️ Deleted record ID {record_id}: '{title}'")
                
                db.commit()
                print(f"✅ Successfully cleaned up {len(orphaned_records)} orphaned records")
            else:
                print("❌ Cleanup cancelled")
        else:
            print("\n✅ No orphaned records found - database is consistent with MinIO")
            
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_orphaned_records()