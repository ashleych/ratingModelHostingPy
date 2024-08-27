from pydantic import ConfigDict, BaseModel
from sqlalchemy import Column, DateTime, UUID

from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import as_declarative, declared_attr

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import enum

from sqlalchemy import Enum as SQLAlchemyEnum
from .base import Base


class FactorInputSource(String):
    USER_INPUT = "user_input"
    FINANCIAL_STATEMENT = "financial_statement"
    DERIVED = "derived"

class FactorType(enum.Enum):
    QUALITATIVE = "qualitative"
    OVERALLSCORE = "overallScore"
    QUANTITATIVE = "quantitative"

class AttributeType(enum.Enum):
    BIN = "bin"
    LOOKUP = "lookup"

class WorkflowActionType(enum.Enum):
    DRAFT = "draft"
    # Add other types as needed

class TemplateSourceCSV(Base):
    source_path = Column(String)

class Template(Base):
    name = Column(String, nullable=False)
    description = Column(String)
    template_source_csv_id = Column(UUID, ForeignKey('templatesourcecsv.id'))
    template_source_csv = relationship("TemplateSourceCSV")

class WorkflowAction(Base):
    customer_id = Column(String, nullable=False)
    action_count_customer_level = Column(Integer)
    action_by = Column(String)
    action_type = Column(String)
    preceding_action_id = Column(UUID, ForeignKey('workflowaction.id'))
    succeeding_action_id = Column(UUID, ForeignKey('workflowaction.id'))
    head = Column(Boolean)

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
    workflow_action_type = Column(String)

class FinancialsPeriod(Base):
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    date = Column(Integer, nullable=False)
    type = Column(String, nullable=False)

class RatingFactorAttribute(Base):
    rating_factor_name = Column(String, ForeignKey('ratingfactor.name'))
    rating_model_id = Column(UUID, ForeignKey('ratingmodel.id'))
    name = Column(String, nullable=False)
    label = Column(String)
    attribute_type = Column(String)
    bin_start = Column(Float)
    bin_end = Column(Float)
    score = Column(Float)

class RatingFactor(Base):
    name = Column(String, unique=True, nullable=False)
    label = Column(String)
    weightage = Column(Float)
    parent_factor_name = Column(String, ForeignKey('ratingfactor.name'))
    parent_factor = relationship("RatingFactor")
    rating_model_id = Column(UUID, ForeignKey('ratingmodel.id'))
    factor_type = Column(String)
    input_source = Column(String)
    order_no = Column(Integer)
    formula = Column(String)
    module = Column(Boolean)
    # factor_value = Column(JSON)  # Storing FactorValue as JSON
    # factor_attributes = relationship("RatingFactorAttribute")

class RatingModule(Base):
    module_name = Column(String, nullable=False)
    module_factor_id = Column(UUID, ForeignKey('ratingfactor.id'))
    module_factor = relationship("RatingFactor")

class RatingModel(Base):
    name = Column(String, nullable=False)
    label = Column(String)
    template_id = Column(UUID, ForeignKey('template.id'))
    template = relationship("Template")
    # qualitative_factors = relationship("RatingFactor", primaryjoin="and_(RatingModel.id==RatingFactor.rating_model_id, RatingFactor.factor_type=='QUALITATIVE')")
    # quantitative_factors = relationship("RatingFactor", primaryjoin="and_(RatingModel.id==RatingFactor.rating_model_id, RatingFactor.factor_type=='QUANTITATIVE')")
    # # qualitative_factors = relationship("RatingFactor")
    # # quantitative_factors = relationship("RatingFactor")
    # quantitative_module = relationship("QuantitativeModule", 
    #                                    primaryjoin="RatingModel.quantitative_module_id == QuantitativeModule.id")
    # qualitative_module = relationship("QualitativeModule", 
    #                                    primaryjoin="RatingModel.qualitative_module_id == QualitativeModule.id")
    

class RatingFactorScore(Base):
    factor_value = Column(JSON)  # Storing FactorValue as JSON
    score_dirty = Column(Boolean)
    rating_instance_id = Column(UUID, ForeignKey('ratinginstance.id'))
    rating_factor_name = Column(String, ForeignKey('ratingfactor.name'))

class RatingInstance(Base):
    rating_instance_front_end_id = Column(String)
    customer_id = Column(UUID, ForeignKey('customer.id'))
    financials_period_id = Column(UUID, ForeignKey('financialsperiod.id'))
    rating_model_id = Column(UUID, ForeignKey('ratingmodel.id'))
    # factor_attribute_map = Column(JSON)  # Storing as JSON
    # factors = relationship("RatingFactor", secondary="rating_instance_factor")
    # quant_factors = relationship("RatingFactor", secondary="rating_instance_quant_factor")
    # qualitative_factors = relationship("RatingFactor", secondary="rating_instance_qualitative_factor")
    # derived_factors = relationship("RatingFactor", secondary="rating_instance_derived_factor")
    # quant_factor_scores = relationship("RatingFactorScore", foreign_keys=[RatingFactorScore.rating_instance_id])
    # qualitative_factor_scores = relationship("RatingFactorScore", foreign_keys=[RatingFactorScore.rating_instance_id])
    # derived_factor_scores = relationship("RatingFactorScore", foreign_keys=[RatingFactorScore.rating_instance_id])
    # factor_scores_map = Column(JSON)  # Storing as JSON
    # factor_scores = relationship("RatingFactorScore", foreign_keys=[RatingFactorScore.rating_instance_id])
    workflow_action_id = Column(UUID, ForeignKey('workflowaction.id'))
    workflow_action_type = Column(String)
    customer = relationship("Customer")
    financials_period = relationship("FinancialsPeriod")
    rating_model = relationship("RatingModel")
    workflow_action = relationship("WorkflowAction")

class LineItemMeta(Base):

    template_id = Column(UUID, ForeignKey('template.id'),nullable=False)
    template = relationship("Template")
    fin_statement_type = Column(String)
    header = Column(Boolean)
    formula = Column(String)
    type = Column(String)
    label = Column(String)
    name = Column(String)
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
    financials_period_id = Column(UUID, ForeignKey('financialsperiod.id'))
    customer_id = Column(UUID, ForeignKey('customer.id'))
    template_id = Column(UUID, ForeignKey('template.id'))
    workflow_action_id = Column(UUID, ForeignKey('workflowaction.id'), nullable=False)
    workflow_action_type = Column(String, default=WorkflowActionType.DRAFT.value)
    is_dirty = Column(Boolean, default=True)
    preferred_statement = Column(Boolean)
    source_of_lag_variables = Column(Integer)

    financials_period = relationship("FinancialsPeriod")
    customer = relationship("Customer")
    template = relationship("Template")
    workflow_action = relationship("WorkflowAction")
    
    
# invoice = Table(
#     "invoice",
#     metadata_obj,
#     Column("invoice_id", Integer, primary_key=True),
#     Column("ref_num", Integer, primary_key=True),
#     Column("description", String(60), nullable=False),
# )

# invoice_item = Table(
#     "invoice_item",
#     metadata_obj,
#     Column("item_id", Integer, primary_key=True),
#     Column("item_name", String(60), nullable=False),
#     Column("invoice_id", Integer, nullable=False),
#     Column("ref_num", Integer, nullable=False),
#     ForeignKeyConstraint(
#         ["invoice_id", "ref_num"], ["invoice.invoice_id", "invoice.ref_num"]
#     ),
# )
# SQLAlchemy model

from sqlalchemy import ForeignKeyConstraint

class LineItemValue(Base):

    financial_statement_id = Column(UUID, ForeignKey('financialstatement.id'))
    line_item_meta_id = Column(UUID, ForeignKey('lineitemmeta.id'))
    value = Column(Float, nullable=True)

    financial_statement = relationship("FinancialStatement")
    line_item_meta = relationship("LineItemMeta")
    
    
    def __repr__(self):
        return f"<LineItemValue(financial_statement_id={self.financial_statement_id}, line_item_meta_id='{self.line_item_meta_id}', value={self.value})>"
