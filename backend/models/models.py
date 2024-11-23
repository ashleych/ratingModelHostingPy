import enum
import string

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (JSON, UUID, Boolean, Column, DateTime, ForeignKey, ForeignKeyConstraint, String, null)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import Session, relationship
from sqlalchemy.sql import func

from .base import Base


class Role(Base):
    name = Column(String,unique=True)
    description= Column(String,nullable=True)
    is_active=Column(Boolean,default=True)
# class WorkflowActionType(enum.Enum):
#     DRAFT = "draft"
    # Add other types as needed

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




