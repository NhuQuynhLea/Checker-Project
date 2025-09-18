from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.config.database import get_db
from app.core.dependencies import get_current_user_dependency, get_current_admin_dependency
from app.models.user import User
from app.services.document_service import DocumentService
from app.schemas.common import BaseResponse
from app.utils.validators import validate_file_upload
import structlog

router = APIRouter(prefix="/reference-documents", tags=["Reference Documents"])
logger = structlog.get_logger(__name__)


@router.get("/", response_model=BaseResponse)
async def get_reference_documents(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get approved reference documents."""
    try:
        document_service = DocumentService(db)
        
        documents = document_service.get_reference_documents(skip=skip, limit=limit)
        total_count = document_service.get_reference_documents_count()
        
        return BaseResponse(
            success=True,
            message="Reference documents retrieved successfully",
            data={
                "documents": [
                    {
                        "document_id": doc.id,
                        "title": doc.title,
                        "created_by": doc.created_by_user.username if doc.created_by_user else "System",
                        "created_at": doc.created_at,
                        "content_type": doc.content_type
                    }
                    for doc in documents
                ],
                "pagination": {
                    "total": total_count,
                    "skip": skip,
                    "limit": limit,
                    "has_more": skip + limit < total_count
                }
            }
        )
        
    except Exception as e:
        logger.error("Failed to get reference documents", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve reference documents"
        )


@router.post("/upload", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def admin_upload_reference_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    admin_user: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Admin direct upload to reference database (bypasses approval)."""
    try:
        validate_file_upload(file)
        
        file_content = await file.read()
        file.file.seek(0)
        
        document_service = DocumentService(db)
        
        # Admin uploads go directly to reference documents
        document = document_service.create_reference_document(
            admin_id=admin_user.id,
            file_data=file.file,
            filename=file.filename,
            content_type=file.content_type,
            file_size=len(file_content),
            title=title
        )
        
        return BaseResponse(
            success=True,
            message="Reference document created successfully",
            data={
                "document_id": document.id,
                "title": document.title,
                "status": "approved",
                "type": "reference_document"
            }
        )
            
    except Exception as e:
        logger.error("Failed to upload reference document", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}"
        )


@router.get("/{document_id}", response_model=BaseResponse)
async def get_reference_document(
    document_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get reference document details."""
    try:
        document_service = DocumentService(db)
        
        document = document_service.get_reference_document(document_id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference document not found")
        
        return BaseResponse(
            success=True,
            message="Reference document retrieved successfully",
            data={
                "document_id": document.id,
                "title": document.title,
                "created_by": document.created_by_user.username if document.created_by_user else "System",
                "created_at": document.created_at,
                "content_type": document.content_type,
                "metadata": document.document_metadata
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get reference document", document_id=document_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve reference document"
        )


@router.delete("/{document_id}", response_model=BaseResponse)
async def delete_reference_document(
    document_id: int,
    admin_user: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Delete reference document (admin only)."""
    try:
        document_service = DocumentService(db)
        
        success = document_service.delete_reference_document(document_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference document not found")
        
        return BaseResponse(
            success=True,
            message="Reference document deleted successfully",
            data={"document_id": document_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete reference document", document_id=document_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete reference document"
        )