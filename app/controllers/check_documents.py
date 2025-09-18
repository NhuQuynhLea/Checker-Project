from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import io
import structlog
from urllib.parse import quote

from app.config.database import get_db
from app.core.dependencies import get_current_user_dependency, get_pagination_params, PaginationParams
from app.core.exceptions import NotFoundException, StorageException
from app.services.check_document_service import CheckDocumentService
from app.services.plagiarism_service import PlagiarismService
from app.models.user import User
from app.schemas.common import BaseResponse, PaginatedResponse
from app.utils.helpers import create_response_metadata

router = APIRouter(prefix="/check-documents", tags=["Check Documents"])
logger = structlog.get_logger(__name__)


@router.get("", response_model=PaginatedResponse)
async def get_check_documents(
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get user's check documents with pagination."""
    try:
        check_document_service = CheckDocumentService(db)
        
        documents = check_document_service.get_user_check_documents(
            user_id=current_user.id,
            skip=pagination.offset,
            limit=pagination.size
        )
        
        total_count = check_document_service.get_user_check_documents_count(current_user.id)
        
        document_responses = [
            {
                "id": doc.id,
                "title": doc.title,
                "content_type": doc.content_type,
                "status": doc.status,
                "created_at": doc.created_at,
                "updated_at": doc.updated_at
            }
            for doc in documents
        ]
        
        metadata = create_response_metadata(pagination.page, pagination.size, total_count, len(documents))
        
        return PaginatedResponse(
            data=document_responses,
            pagination=metadata["pagination"]
        )
        
    except Exception as e:
        logger.error("Failed to get check documents", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to retrieve documents"
        )


@router.get("/{document_id}", response_model=BaseResponse)
async def get_check_document(
    document_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get check document details."""
    try:
        check_document_service = CheckDocumentService(db)
        plagiarism_service = PlagiarismService(db)
        
        document = check_document_service.get_check_document(document_id, current_user.id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        
        # Get plagiarism checks for this document
        checks = plagiarism_service.get_document_plagiarism_checks(document.id)
        
        return BaseResponse(
            message="Document retrieved successfully",
            data={
                "id": document.id,
                "title": document.title,
                "content_type": document.content_type,
                "status": document.status,
                "created_at": document.created_at,
                "updated_at": document.updated_at,
                "plagiarism_checks": [
                    {
                        "check_id": check.id,
                        "similarity_score": check.total_similarity_score,
                        "status": check.check_status,
                        "checked_at": check.created_at
                    }
                    for check in checks
                ]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get check document", document_id=document_id, user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document"
        )


@router.get("/{document_id}/download")
async def download_check_document(
    document_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Download check document file."""
    try:
        check_document_service = CheckDocumentService(db)
        
        # Check if document exists first
        document = check_document_service.get_check_document(document_id, current_user.id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        
        # Download the file content
        file_content = check_document_service.download_check_document(document_id, current_user.id)
        
        # Properly encode filename for Content-Disposition header
        encoded_filename = quote(document.title.encode('utf-8'))
        
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=document.content_type or "application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
        
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except StorageException as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Storage error: {str(e)}")
    except Exception as e:
        logger.error("Failed to download check document", document_id=document_id, user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to download document")


@router.delete("/{document_id}", response_model=BaseResponse)
async def delete_check_document(
    document_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Delete check document."""
    try:
        check_document_service = CheckDocumentService(db)
        
        success = check_document_service.delete_check_document(document_id, current_user.id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        
        return BaseResponse(
            message="Document deleted successfully",
            data={"document_id": document_id}
        )
        
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Failed to delete check document", document_id=document_id, user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )