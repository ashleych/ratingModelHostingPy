import string
from pydantic import ConfigDict, BaseModel
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy import Column, DateTime, UUID, null

from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import as_declarative, declared_attr

from sqlalchemy import Column, String, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import enum

from .base import Base
from sqlalchemy.orm import Session



class Role(Base):
    name = Column(String)
    description= Column(String,nullable=True)
    is_active=Column(Boolean,default=True)
# class WorkflowActionType(enum.Enum):
#     DRAFT = "draft"
    # Add other types as needed

class TemplateSourceCSV(Base):
    source_path = Column(String)

class User(Base):
    __table__name= 'users'
    model_config = ConfigDict(from_attributes=True)
    email = Column(String, unique=True)
    password = Column(String, nullable=False)   
    name = Column(String )
    role = Column(JSON, nullable= True)

class BusinessUnit(Base):
    name = Column(String, unique=True, nullable=False)
    template_id = Column(UUID, ForeignKey('template.id'),nullable=True)
    template = relationship("Template")

class MasterRatingScale(Base):
    rating_grade = Column(String, unique=True, nullable=False)
    pd = Column(Float, nullable=False)
class Customer(Base):
    customer_name = Column(String, nullable=False)
    cif_number = Column(String, nullable=False)
    group_name = Column(String, nullable=False)
    business_unit_id = Column(UUID, ForeignKey('businessunit.id'))
    business_unit = relationship("BusinessUnit")
    relationship_type = Column(String, nullable=False)
    internal_risk_rating = Column(String, ForeignKey('masterratingscale.rating_grade'))
    master_rating_scale = relationship("MasterRatingScale")
    workflow_action_id = Column(UUID, ForeignKey('workflowaction.id'))
    workflow_action = relationship("WorkflowAction")




