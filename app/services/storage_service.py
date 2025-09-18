from typing import Optional, BinaryIO
from minio import Minio
from minio.error import S3Error
import structlog
import threading
import os

from app.config.settings import get_settings
from app.core.exceptions import StorageException
from app.utils.helpers import generate_unique_filename

settings = get_settings()
logger = structlog.get_logger(__name__)


class StorageService:
    """Service for handling file storage operations with MinIO."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(StorageService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    # def __init__(self):
    #     if not self._initialized:
    #         self.client = None
    #         self.bucket_name = settings.minio_bucket_name
    #         self.is_connected = False
    #         self._initialize_client()
    #         self._initialized = True
    
    def __init__(self):
        if not self._initialized:
            self.client = None
            self.bucket_name = settings.minio_bucket_name
            self.is_connected = False
            try:
                self._initialize_client()
            except Exception as e:
                logger.error(f"Storage service initialization failed: {e}")
                self.client = None
                self.is_connected = False
            self._initialized = True

    def _initialize_client(self):
        """Initialize MinIO client with connection validation."""
        try:
            # Use settings-based configuration for proper environment detection
            client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure
            )
            
            # Test connection by listing buckets
            list(client.list_buckets())

            # Only assign to self.client if connection succeeds
            self.client = client
            self.is_connected = True
            self._ensure_bucket_exists()
            
            logger.info(
                "MinIO connection established",
                endpoint=settings.minio_endpoint,
                bucket=self.bucket_name,
                secure=settings.minio_secure
            )
            
        except Exception as e:
            logger.error(
                "Failed to initialize MinIO client",
                endpoint=settings.minio_endpoint,
                error=str(e)
            )
            self.is_connected = False
            self.client = None
    
    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info("Created MinIO bucket", bucket=self.bucket_name)
        except S3Error as e:
            logger.error("Failed to create bucket", bucket=self.bucket_name, error=str(e))
            raise StorageException(f"Failed to create storage bucket: {e}")
    
    def _retry_connection(self):
        """Attempt to reconnect to MinIO."""
        if not self.is_connected and self.client is None:
            logger.info("Attempting to reconnect to MinIO")
            self._initialize_client()
    
    def upload_file(
        self, 
        file_data: BinaryIO, 
        original_filename: str,
        content_type: str,
        file_size: int
    ) -> str:
        """Upload a file and return the object ID."""
        # Remove the mock storage logic since we have proper MinIO config now
            
        # Try to reconnect if not connected
        if not self.is_connected:
            self._retry_connection()
            
        if not self.is_connected or not self.client:
            raise StorageException("MinIO storage is not available. Please check your MinIO configuration.")
            
        try:
            object_id = generate_unique_filename(original_filename)
            
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_id,
                data=file_data,
                length=file_size,
                content_type=content_type
            )
            
            logger.info(
                "File uploaded successfully",
                object_id=object_id,
                original_filename=original_filename,
                size=file_size
            )
            
            return object_id
            
        except S3Error as e:
            logger.error("Failed to upload file", error=str(e))
            raise StorageException(f"Failed to upload file: {e}")
    
    def download_file(self, object_id: str) -> bytes:
        """Download a file by object ID."""
        if not self.is_connected or not self.client:
            raise StorageException("MinIO storage is not available. Please check your MinIO configuration.")
            
        try:
            response = self.client.get_object(self.bucket_name, object_id)
            data = response.read()
            response.close()
            response.release_conn()
            
            logger.info("File downloaded successfully", object_id=object_id)
            return data
            
        except S3Error as e:
            logger.error("Failed to download file", object_id=object_id, error=str(e))
            raise StorageException(f"Failed to download file: {e}")
    
    def delete_file(self, object_id: str) -> bool:
        """Delete a file by object ID."""
        if not self.is_connected or not self.client:
            raise StorageException("MinIO storage is not available. Please check your MinIO configuration.")
            
        try:
            self.client.remove_object(self.bucket_name, object_id)
            logger.info("File deleted successfully", object_id=object_id)
            return True
            
        except S3Error as e:
            logger.error("Failed to delete file", object_id=object_id, error=str(e))
            raise StorageException(f"Failed to delete file: {e}")
    
    def get_file_info(self, object_id: str) -> Optional[dict]:
        """Get file information by object ID."""
        try:
            stat = self.client.stat_object(self.bucket_name, object_id)
            return {
                "object_id": object_id,
                "size": stat.size,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified,
                "etag": stat.etag
            }
            
        except S3Error as e:
            logger.error("Failed to get file info", object_id=object_id, error=str(e))
            return None
    
    def file_exists(self, object_id: str) -> bool:
        """Check if a file exists."""
        try:
            self.client.stat_object(self.bucket_name, object_id)
            return True
        except S3Error:
            return False
