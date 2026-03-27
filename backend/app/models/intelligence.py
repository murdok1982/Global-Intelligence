from sqlalchemy import Column, String, ForeignKey, DateTime, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.db.base import Base
from sqlalchemy.orm import relationship

class IntelligenceCategory(Base):
    __tablename__ = "intelligence_categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False) # Economic, Political, Military, Social, Security.

class IntelligenceItem(Base):
    __tablename__ = "intelligence_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_id = Column(UUID(as_uuid=True), ForeignKey("countries.id"))
    category_id = Column(UUID(as_uuid=True), ForeignKey("intelligence_categories.id"))
    agent_source = Column(String, nullable=False) # e.g. osint_agent, public_signals, contributor
    content = Column(String, nullable=False) # Structured markdown or plain text 
    confidence_score = Column(Float, default=0.0) # 0.0 to 1.0
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
class SourceRegistry(Base):
    __tablename__ = "source_registry"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String, unique=True, nullable=False)
    source_type = Column(String, nullable=False) # e.g. news, official, social
    credibility_score = Column(Float, default=0.5)
    last_scraped = Column(DateTime, nullable=True)
