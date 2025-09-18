from typing import Optional, List, BinaryIO
from sqlalchemy.orm import Session
import structlog

from app.models.check_document import CheckDocument
from app.models.user import User
from app.services.storage_service import StorageService
from app.core.exceptions import NotFoundException, AuthorizationException, ValidationException

logger = structlog.get_logger(__name__)


class CheckDocumentService:
    """Service for check document management operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.storage_service = StorageService()
    
    def upload_check_document(
        self,
        user_id: int,
        file_data: BinaryIO,
        filename: str,
        content_type: str,
        file_size: int,
        title: Optional[str] = None
    ) -> CheckDocument:
        """Upload a document for plagiarism checking."""
        try:
            # Upload file to storage first
            object_id = self.storage_service.upload_file(
                file_data=file_data,
                original_filename=filename,
                content_type=content_type,
                file_size=file_size
            )
            
            # Create database record only after successful storage upload
            document = CheckDocument(
                user_id=user_id,
                title=title or filename,
                object_id=object_id,
                content_type=content_type,
                status="active"
            )
            
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            
            logger.info(
                "Check document uploaded",
                document_id=document.id,
                user_id=user_id,
                filename=filename
            )
            
            return document
            
        except Exception as e:
            # Ensure database session is clean on any failure
            try:
                self.db.rollback()
            except Exception as rollback_error:
                logger.warning("Failed to rollback database session", error=str(rollback_error))
            
            logger.error("Failed to upload check document", error=str(e), exc_info=True)
            raise
    
    def get_check_document(self, document_id: int, user_id: Optional[int] = None) -> Optional[CheckDocument]:
        """Get check document by ID."""
        query = self.db.query(CheckDocument).filter(CheckDocument.id == document_id)
        
        if user_id:
            query = query.filter(CheckDocument.user_id == user_id)
        
        return query.first()
    
    def get_user_check_documents(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[CheckDocument]:
        """Get user's check documents."""
        return self.db.query(CheckDocument).filter(
            CheckDocument.user_id == user_id,
            CheckDocument.status == "active"
        ).order_by(CheckDocument.created_at.desc()).offset(skip).limit(limit).all()
    
    def get_user_check_documents_count(self, user_id: int) -> int:
        """Get count of user's check documents."""
        return self.db.query(CheckDocument).filter(
            CheckDocument.user_id == user_id,
            CheckDocument.status == "active"
        ).count()
    
    def download_check_document(self, document_id: int, user_id: int) -> bytes:
        """Download check document content."""
        document = self.get_check_document(document_id, user_id)
        if not document:
            raise NotFoundException("Document not found")
        
        if document.status != "active":
            raise NotFoundException("Document not available")
        
        return self.storage_service.download_file(document.object_id)
    
    def delete_check_document(self, document_id: int, user_id: int) -> bool:
        """Delete check document (soft delete)."""
        document = self.get_check_document(document_id, user_id)
        if not document:
            raise NotFoundException("Document not found")
        
        # Soft delete - mark as deleted instead of physically removing
        document.status = "deleted"
        self.db.commit()
        
        logger.info("Check document deleted", document_id=document_id, user_id=user_id)
        return True
    
    def get_check_documents_with_plagiarism_history(
        self, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 20
    ) -> List[CheckDocument]:
        """Get user's check documents with their plagiarism check history."""
        return self.db.query(CheckDocument).filter(
            CheckDocument.user_id == user_id,
            CheckDocument.status == "active"
        ).order_by(CheckDocument.created_at.desc()).offset(skip).limit(limit).all()