from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List

from app.config.database import get_db
from app.core.dependencies import get_current_user_dependency, get_current_admin_dependency
from app.models.user import User
from app.services.document_service import DocumentService
from app.schemas.common import BaseResponse
from app.schemas.document import UserDocumentResponse, ReferenceDocumentResponse
from app.utils.validators import validate_file_upload
import structlog

router = APIRouter(prefix="/reference-submissions", tags=["Reference Submissions"])
logger = structlog.get_logger(__name__)


@router.post("/upload", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def submit_reference_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Submit reference document for approval.
    - Users: Creates pending document requiring admin approval
    - Admins: Creates approved reference document immediately
    """
    try:
        validate_file_upload(file)
        
        file_content = await file.read()
        file.file.seek(0)
        
        document_service = DocumentService(db)
        
        if current_user.is_admin:
            # Admin uploads go directly to reference documents
            document = document_service.create_reference_document(
                admin_id=current_user.id,
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
                    "type": "reference"
                }
            )
        else:
            # User uploads go to user documents with pending status
            document = document_service.upload_user_document(
                user_id=current_user.id,
                file_data=file.file,
                filename=file.filename,
                content_type=file.content_type,
                file_size=len(file_content),
                title=title
            )
            
            return BaseResponse(
                success=True,
                message="Reference document submitted successfully. Awaiting admin approval.",
                data={
                    "document_id": document.id,
                    "title": document.title,
                    "status": "pending",
                    "type": "reference_submission"
                }
            )
            
    except Exception as e:
        logger.error("Failed to submit reference document", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit document: {str(e)}"
        )


@router.get("/pending", response_model=BaseResponse)
async def get_pending_submissions(
    skip: int = 0,
    limit: int = 20,
    admin_user: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Get pending reference document submissions awaiting approval."""
    try:
        document_service = DocumentService(db)
        
        documents = document_service.get_pending_documents(skip=skip, limit=limit)
        total_count = document_service.get_pending_documents_count()
        
        return BaseResponse(
            success=True,
            message="Pending submissions retrieved successfully",
            data={
                "documents": [
                    {
                        "submission_id": doc.id,
                        "title": doc.title,
                        "submitted_by": doc.user.username,
                        "submitted_at": doc.created_at,
                        "content_type": doc.content_type,
                        "status": doc.status
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
        logger.error("Failed to get pending submissions", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve pending submissions"
        )


@router.post("/{submission_id}/approve", response_model=BaseResponse)
async def approve_reference_submission(
    submission_id: int,
    comment: Optional[str] = Form(None),
    admin_user: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Approve reference document submission for inclusion in reference database."""
    try:
        document_service = DocumentService(db)
        
        approved_document = document_service.approve_user_document(
            document_id=submission_id,
            admin_id=admin_user.id,
            comment=comment
        )
        
        return BaseResponse(
            success=True,
            message="Submission approved and added to reference database",
            data={
                "submission_id": approved_document.id,
                "title": approved_document.title,
                "status": approved_document.status,
                "approved_by": admin_user.username,
                "comment": comment
            }
        )
        
    except Exception as e:
        logger.error("Failed to approve submission", submission_id=submission_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve submission: {str(e)}"
        )


@router.post("/{submission_id}/reject", response_model=BaseResponse)
async def reject_reference_submission(
    submission_id: int,
    comment: str = Form(...),
    admin_user: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Reject reference document submission."""
    try:
        document_service = DocumentService(db)
        
        rejected_document = document_service.reject_user_document(
            document_id=submission_id,
            admin_id=admin_user.id,
            comment=comment
        )
        
        return BaseResponse(
            success=True,
            message="Submission rejected",
            data={
                "submission_id": rejected_document.id,
                "title": rejected_document.title,
                "status": rejected_document.status,
                "rejected_by": admin_user.username,
                "comment": comment
            }
        )
        
    except Exception as e:
        logger.error("Failed to reject submission", submission_id=submission_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject submission: {str(e)}"
        )


@router.get("/my-submissions", response_model=BaseResponse)
async def get_my_submissions(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get user's reference document submissions."""
    try:
        document_service = DocumentService(db)
        
        documents = document_service.get_user_documents(
            user_id=current_user.id,
            skip=skip,
            limit=limit
        )
        total_count = document_service.get_user_documents_count(current_user.id)
        
        return BaseResponse(
            success=True,
            message="User submissions retrieved successfully",
            data={
                "submissions": [
                    {
                        "submission_id": doc.id,
                        "title": doc.title,
                        "status": doc.status,
                        "submitted_at": doc.created_at,
                        "content_type": doc.content_type,
                        "comment": doc.comment if doc.status in ['approved', 'rejected'] else None
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
        logger.error("Failed to get user submissions", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve submissions"
        )
