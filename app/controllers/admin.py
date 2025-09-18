from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.config.database import get_db
from app.core.dependencies import get_current_admin_dependency, get_pagination_params, PaginationParams
from app.services.admin_service import AdminService
from app.services.user_service import UserService
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.common import BaseResponse, PaginatedResponse
from app.utils.helpers import create_response_metadata

router = APIRouter()


@router.get("/stats", response_model=BaseResponse)
async def get_system_statistics(
    current_admin: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Get comprehensive system statistics."""
    admin_service = AdminService(db)
    stats = admin_service.get_system_statistics()
    
    return BaseResponse(
        message="System statistics retrieved successfully",
        data=stats
    )


@router.get("/stats/activity", response_model=BaseResponse)
async def get_activity_stats(
    days: int = 30,
    current_admin: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Get user activity statistics over time."""
    admin_service = AdminService(db)
    activity_stats = admin_service.get_user_activity_stats(days)
    
    return BaseResponse(
        message="Activity statistics retrieved successfully",
        data=activity_stats
    )


@router.get("/stats/similarity-distribution", response_model=BaseResponse)
async def get_similarity_distribution(
    current_admin: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Get similarity score distribution."""
    admin_service = AdminService(db)
    distribution = admin_service.get_similarity_distribution()
    
    return BaseResponse(
        message="Similarity distribution retrieved successfully",
        data=distribution
    )


@router.get("/users", response_model=PaginatedResponse)
async def get_all_users(
    pagination: PaginationParams = Depends(get_pagination_params),
    current_admin: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Get all users with pagination."""
    user_service = UserService(db)
    
    users = user_service.get_users(skip=pagination.offset, limit=pagination.size)
    total_count = user_service.get_users_count()
    
    user_responses = [UserResponse.from_orm(user) for user in users]
    metadata = create_response_metadata(pagination.page, pagination.size, total_count, len(users))
    
    return PaginatedResponse(
        data=user_responses,
        pagination=metadata["pagination"]
    )


@router.put("/users/{user_id}", response_model=BaseResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_admin: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Update user information."""
    user_service = UserService(db)
    
    try:
        updated_user = user_service.update_user(user_id, user_data)
        return BaseResponse(
            message="User updated successfully",
            data=UserResponse.from_orm(updated_user)
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/users/{user_id}/ban", response_model=BaseResponse)
async def ban_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Ban a user."""
    user_service = UserService(db)
    
    try:
        banned_user = user_service.ban_user(user_id)
        return BaseResponse(
            message="User banned successfully",
            data=UserResponse.from_orm(banned_user)
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/users/{user_id}/unban", response_model=BaseResponse)
async def unban_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """Unban a user."""
    user_service = UserService(db)
    
    try:
        unbanned_user = user_service.unban_user(user_id)
        return BaseResponse(
            message="User unbanned successfully",
            data=UserResponse.from_orm(unbanned_user)
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
