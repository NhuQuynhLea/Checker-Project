#!/usr/bin/env python3
"""
MinIO Diagnostic Script
Check MinIO connection, buckets, and files
"""

import os
from minio import Minio
from minio.error import S3Error
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_minio_connection():
    """Check MinIO connection and diagnose issues."""
    print("🔍 MinIO Diagnostic Report")
    print("=" * 50)
    
    # Read configuration
    endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9090')
    access_key = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
    secret_key = os.getenv('MINIO_SECRET_KEY', 'minioadmin123')
    bucket_name = os.getenv('MINIO_BUCKET_NAME', 'plagiarism')
    secure = os.getenv('MINIO_SECURE', 'false').lower() == 'true'
    
    print(f"📋 Configuration:")
    print(f"   Endpoint: {endpoint}")
    print(f"   Access Key: {access_key}")
    print(f"   Bucket Name: {bucket_name}")
    print(f"   Secure (HTTPS): {secure}")
    print()
    
    try:
        # Initialize MinIO client
        print("🔌 Testing MinIO connection...")
        client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        
        # Test connection
        buckets = list(client.list_buckets())
        print("✅ Connection successful!")
        print(f"📂 Found {len(buckets)} bucket(s):")
        for bucket in buckets:
            print(f"   - {bucket.name} (created: {bucket.creation_date})")
        print()
        
        # Check specific bucket
        if client.bucket_exists(bucket_name):
            print(f"✅ Bucket '{bucket_name}' exists")
            
            # List objects in bucket
            objects = list(client.list_objects(bucket_name, recursive=True))
            print(f"📄 Found {len(objects)} object(s) in bucket '{bucket_name}':")
            
            if objects:
                for obj in objects:
                    print(f"   - {obj.object_name}")
                    print(f"     Size: {obj.size} bytes")
                    print(f"     Modified: {obj.last_modified}")
                    print()
            else:
                print("   (No objects found)")
                
        else:
            print(f"❌ Bucket '{bucket_name}' does not exist")
            print("🔧 Attempting to create bucket...")
            try:
                client.make_bucket(bucket_name)
                print(f"✅ Bucket '{bucket_name}' created successfully")
            except Exception as e:
                print(f"❌ Failed to create bucket: {e}")
        
    except S3Error as e:
        print(f"❌ MinIO S3 Error: {e}")
        print(f"   Code: {e.code}")
        print(f"   Message: {e.message}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   1. Check if MinIO container is running: docker-compose ps")
        print("   2. Verify MinIO is accessible: http://localhost:9001")
        print("   3. Check credentials in MinIO web interface")
        print("   4. Ensure port 9090 is not blocked")

if __name__ == "__main__":
    check_minio_connection()