from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from datetime import datetime
from app.db.base import Base
from sqlalchemy.orm import relationship

class RoleEnum(str, enum.Enum):
    user = "user"
    institutional = "institutional"
    admin = "admin"

class PlanTypeEnum(str, enum.Enum):
    individual = "individual"
    institutional = "institutional"

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.user, nullable=False)
    is_active = Column(Boolean, default=True)
    two_factor_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    subscription = relationship("Subscription", back_populates="user", uselist=False)

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    plan_type = Column(Enum(PlanTypeEnum), nullable=False)
    status = Column(String, default="inactive") # active, past_due, canceled
    current_period_end = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="subscription")
