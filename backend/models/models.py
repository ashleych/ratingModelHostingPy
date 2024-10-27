import string
from pydantic import ConfigDict, BaseModel
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy import Column, DateTime, UUID, null

from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import as_declarative, declared_attr

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, JSON,UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import enum

from sqlalchemy import Enum as SQLAlchemyEnum
from .base import Base
from typing import List
from sqlalchemy.orm import Session

from schema.schema import WorkflowStatus
class FactorInputSource(enum.Enum):
    USER_INPUT = "user_input"
    FINANCIAL_STATEMENT = "financial_statement"
    DERIVED = "derived"

class FactorType(enum.Enum):
    QUALITATIVE = "qualitative"
    OVERALLSCORE = "overallScore"
    QUANTITATIVE = "quantitative"
    OVERALL="overall"

class AttributeType(enum.Enum):
    BIN = "bin"
    LOOKUP = "lookup"

class WorkflowActionType(enum.Enum):
    DRAFT = "draft"
    # Add other types as needed

class TemplateSourceCSV(Base):
    source_path = Column(String)

class User(Base):
    __table__name= 'users'
    model_config = ConfigDict(from_attributes=True)
    email = Column(String, unique=True)
    password = Column(String, nullable=False)   
    name = Column(String )
    role = Column(String)
class Template(Base):
    name = Column(String, nullable=False)
    description = Column(String)
    template_source_csv_id = Column(UUID, ForeignKey('templatesourcecsv.id'))
    template_source_csv = relationship("TemplateSourceCSV")

class WorkflowAction(Base):
    __tablename__ = 'workflowaction'

    workflow_cycle_id=Column(UUID, nullable=False) 
    customer_id = Column(UUID, nullable=False)
    action_count_customer_level = Column(Integer)
    action_by = Column(UUID)
    description=Column(String)
    action_type = Column(SQLAlchemyEnum(WorkflowStatus), nullable=False, default=WorkflowStatus.DRAFT)
    preceding_action_id = Column(UUID, ForeignKey('workflowaction.id'))
    succeeding_action_id = Column(UUID, ForeignKey('workflowaction.id'))
    # rating_instance_id_received = Column(UUID(as_uuid=True), ForeignKey('ratinginstance.id'), nullable=True)
    rating_instance_id = Column(UUID(as_uuid=True), ForeignKey('ratinginstance.id'), nullable=True)
    head = Column(Boolean,default=True)

    rating_instance = relationship("RatingInstance", back_populates="workflow_actions")  # not workflow_actions


class RatingInstance(Base):
    # rating_instance_front_end_id = Column(String)
    customer_id = Column(UUID, ForeignKey('customer.id'),nullable=False)

    financial_statement_id = Column(UUID, ForeignKey('financialstatement.id'),nullable=False)
    rating_model_id = Column(UUID, ForeignKey('ratingmodel.id'))
    # workflow_action_id = Column(UUID, ForeignKey('workflowaction.id'))
    # workflow_action_type = Column(String)
    inputs_completion_status=Column(Boolean,default=False)
    incomplete_financial_information =Column(Boolean,default=False)
    missing_financial_fields = Column(JSON, default={})
    overall_score=Column(Float,nullable=True)
    overall_rating=Column(String,nullable=True)
    overall_status = Column(SQLAlchemyEnum(WorkflowStatus), nullable=False, default=WorkflowStatus.DRAFT)

    customer = relationship("Customer")
    rating_model = relationship("RatingModel")
    workflow_actions = relationship("WorkflowAction",back_populates='rating_instance')
    
    @property
    def current_workflow_action(self):
        """Get the most recent workflow action"""
        return max(self.workflow_actions, key=lambda x: x.action_count_customer_level) if self.workflow_actions else None

class BusinessUnit(Base):
    name = Column(String, unique=True, nullable=False)

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
    # workflow_action_type = Column(String)

class FinancialsPeriod(Base):
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    date = Column(Integer, nullable=False)
    type = Column(String, nullable=False)


class RatingFactor(Base):
    __tablename__ = 'ratingfactor'

    name = Column(String, nullable=False)
    label = Column(String)
    input_source = Column(String)
    order_no = Column(Integer)
    factor_type = Column(String)
    parent_factor_name = Column(String)
    weightage = Column(Float)
    module_name = Column(String)
    module_order = Column(Integer)  # New field for module order
    formula = Column(String)
    rating_model_id = Column(UUID, ForeignKey('ratingmodel.id'), nullable=False)

    rating_model = relationship("RatingModel")
    __table_args__ = (UniqueConstraint('rating_model_id', 'name', name='uix_rating_model_factorname'),)
class RatingFactorAttribute(Base):

    rating_model_id = Column(UUID, ForeignKey('ratingmodel.id'),nullable=False)
    rating_factor_id = Column(UUID, ForeignKey('ratingfactor.id'),nullable=False)
    rating_factor_name = Column(String)
    name = Column(String)
    label = Column(String)
    attribute_type = Column(String)
    bin_start = Column(Float)
    bin_end = Column(Float)
    score = Column(Float)

    rating_factor = relationship("RatingFactor")
    rating_model = relationship("RatingModel")

class ScoreToGradeMapping(Base):
    rating_model_id = Column(UUID, ForeignKey('ratingmodel.id'),nullable=False)
    bin_start=Column(Float)
    bin_end=Column(Float)
    grade=Column(String)
    
    rating_model = relationship("RatingModel")

class RatingModel(Base):

    name = Column(String, unique=True)
    label = Column(String)
    template_id = Column(UUID, ForeignKey('template.id'),nullable=False)

    template = relationship("Template")



class LineItemMeta(Base):
    __table_args__ = (
        UniqueConstraint('template_id', 'name', name='uix_template_name'),
    )
    template_id = Column(UUID, ForeignKey('template.id'),nullable=False)
    template = relationship("Template")
    fin_statement_type = Column(String)
    header = Column(Boolean)
    formula = Column(String)
    type = Column(String)
    label = Column(String)
    name = Column(String,nullable=False)
    lag_months = Column(Integer)
    display = Column(Boolean)
    order_no = Column(Integer)
    display_order_no = Column(Integer)


class FinancialStatement(Base):

    actuals = Column(Boolean)
    projections = Column(Boolean)
    audit_type = Column(String)  # Audited, Unaudited
    standalone = Column(Boolean)
    consolidated = Column(Boolean)
    financials_period_year = Column(Integer)
    financials_period_month = Column( Integer)
    financials_period_date = Column( Integer)
    customer_id = Column(UUID, ForeignKey('customer.id'),nullable=False)
    template_id = Column(UUID, ForeignKey('template.id'),nullable=False)
    # workflow_action_id = Column(UUID, ForeignKey('workflowaction.id'), nullable=False)
    # workflow_action_type = Column(String, default=WorkflowActionType.DRAFT.value)
    is_dirty = Column(Boolean, default=True)
    preferred_statement = Column(Boolean)
    source_of_lag_variables = Column(Integer)
    preceding_statement_id=Column(UUID)
    
    customer = relationship("Customer")
    template = relationship("Template")
    # workflow_action = relationship("WorkflowAction")

class RatingFactorScore(Base):

    # FactorValue embedded struct
    raw_value_text = Column(String)
    raw_value_float = Column(Float)
    score = Column(Float)

    score_dirty = Column(Boolean, default=True)
    rating_instance_id = Column(UUID, ForeignKey('ratinginstance.id', onupdate="CASCADE", ondelete="CASCADE"))
    rating_factor_id = Column(UUID, ForeignKey('ratingfactor.id', onupdate="CASCADE", ondelete="CASCADE"))

    rating_instance = relationship("RatingInstance")
    rating_factor = relationship("RatingFactor")
    __table_args__ = ( UniqueConstraint('rating_instance_id', 'rating_factor_id', name='uix_ratinginstance_ratingfactor'), )


class LineItemValue(Base):

    financial_statement_id = Column(UUID, ForeignKey('financialstatement.id'),nullable=False)
    line_item_meta_id = Column(UUID, ForeignKey('lineitemmeta.id'),nullable=False)
    value = Column(Float, nullable=True)
    financial_statement = relationship("FinancialStatement")
    line_item_meta = relationship("LineItemMeta")
    __table_args__ = ( UniqueConstraint('financial_statement_id', 'line_item_meta_id', name='uix_financial_statement_line_item'), )
    
    def __repr__(self):
        return f"<LineItemValue(financial_statement_id={self.financial_statement_id}, line_item_meta_id='{self.line_item_meta_id}', value={self.value})>"
