from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.config.database import Base
from app.models.base import TimestampMixin


class CheckDocument(Base, TimestampMixin):
    """
    Documents uploaded for plagiarism checking only.
    These documents don't need approval workflow - they are immediately available for checking.
    """
    __tablename__ = "check_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    object_id = Column(String(255), unique=True, nullable=False)
    content_type = Column(String(100))
    status = Column(String(20), default="active", nullable=False)  # 'active' | 'deleted'
    
    # Relationships
    user = relationship("User", back_populates="check_documents")
    plagiarism_checks = relationship("PlagiarismCheck", back_populates="check_document", cascade="all, delete-orphan")