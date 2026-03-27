from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.db.base import Base

class DailyReport(Base):
    __tablename__ = "daily_reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_id = Column(UUID(as_uuid=True), ForeignKey("countries.id"))
    report_date = Column(DateTime, default=datetime.utcnow)
    executive_summary = Column(Text, nullable=False)
    content_json = Column(Text, nullable=False) # Store the structural UI representation
    published = Column(Boolean, default=False)
    
class PremiumReport(Base):
    __tablename__ = "premium_reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    request_topic = Column(String, nullable=False)
    content_markdown = Column(Text, nullable=False)
    human_reviewed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ReportCitation(Base):
    __tablename__ = "report_citations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_registry_id = Column(UUID(as_uuid=True), ForeignKey("source_registry.id"))
    report_type = Column(String, nullable=False) # 'daily' or 'premium'
    report_id = Column(UUID(as_uuid=True), nullable=False)
