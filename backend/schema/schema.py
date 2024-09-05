from pydantic import BaseModel, Field,ConfigDict
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum
from uuid import UUID

class Base(BaseModel):
    id: Optional[UUID] = Field(None, description="Unique identifier")
    created_at: Optional[datetime] = Field(None, description="Creation datetime")
    updated_at: Optional[datetime] = Field(None, description="Update datetime")

class FactorInputSource(str, Enum):
    USER_INPUT = "user_input"
    FINANCIAL_STATEMENT = "financial_statement"
    DERIVED = "derived"

class FactorType(str, Enum):
    QUALITATIVE = "qualitative"
    OVERALLSCORE = "overallScore"
    QUANTITATIVE = "quantitative"

class AttributeType(str, Enum):
    BIN = "bin"
    LOOKUP = "lookup"

class WorkflowActionType(str, Enum):
    DRAFT = "draft"  # Example value, add others as needed

class FactorValue(BaseModel):
    raw_value_text: str = Field(..., alias="rawValueText")
    raw_value_float: float = Field(..., alias="rawValueFloat")
    score: float

class TemplateSourceCSV(Base):
    source_path: str = Field(..., alias="sourcePath")

class Template(Base):
    name: str
    description: str
    template_source_csv: TemplateSourceCSV = Field(..., alias="templateSourceCSV")
    template_source_csv_id: int = Field(..., alias="templateSourceCSVID")

class WorkflowAction(Base):
    customer_id: str = Field(..., alias="customerId")
    action_count_customer_level: int = Field(..., alias="actionCountCustomerLevel")
    action_by: str = Field(..., alias="actionBy")
    action_type: WorkflowActionType = Field(..., alias="workflowActionType")
    preceding_action_id: Optional[int] = Field(None, alias="precedingActionId")
    succeeding_action_id: Optional[int] = Field(None, alias="succeedingActionId")
    head: bool

class BusinessUnit(Base):
    name: str

class MasterRatingScale(Base):
    rating_grade: str = Field(..., alias="ratingGrade")
    pd: float

class Customer(Base):
    customer_name: str = Field(..., alias="customerName")
    cif_number: str = Field(..., alias="cifNumber")
    group_name: str = Field(..., alias="groupName")
    business_unit: BusinessUnit = Field(..., alias="businessUnit")
    business_unit_id: str = Field(..., alias="businessUnitId")
    relationship_type: str = Field(..., alias="relationshipType")
    internal_risk_rating: str = Field(..., alias="internalRiskRating")
    master_rating_scale: MasterRatingScale = Field(..., alias="masterRatingScale")
    workflow_action_id: Optional[int] = Field(None, alias="workflowActionId")
    workflow_action: WorkflowAction = Field(..., alias="workflowaction")
    workflow_action_type: WorkflowActionType = Field(..., alias="workflowActionType")

class CustomerHistory(BaseModel):
    workflow_actions: List[WorkflowAction] = Field([], alias="workFlowActions")
    customers: List[Customer] = Field([], alias="customers")
    rating_instances: List['RatingInstance'] = Field([], alias="ratingInstances")

class RatingFactorAttribute(Base):
    rating_factor_name: str = Field(..., alias="ratingFactorName")
    rating_model_id: int = Field(..., alias="ratingModelID")
    name: str
    label: str
    attribute_type: AttributeType = Field(..., alias="attributeType")
    bin_start: Optional[float] = Field(None, alias="binStart")
    bin_end: Optional[float] = Field(None, alias="binEnd")
    score: float

class RatingFactor(Base):
    name: str
    label: str
    weightage: float
    parent_factor: Optional['RatingFactor'] = Field(None, alias="parentFactor")
    parent_factor_name: Optional[str] = Field(None, alias="parentFactorName")
    rating_model_id: int = Field(..., alias="ratingModelID")
    factor_type: FactorType = Field(..., alias="factorType")
    input_source: FactorInputSource = Field(..., alias="inputSource")
    order_no: int = Field(..., alias="orderNo")
    formula: str
    module: bool
    factor_value: FactorValue = Field(..., alias="factorValue")
    factor_attributes: List[RatingFactorAttribute] = Field([], alias="factorAttributes")

class RatingModule(BaseModel):
    module_name: str = Field(..., alias="moduleName")
    module_factor: RatingFactor = Field(..., alias="moduleFactor")
    child_factors_in_module: List[RatingFactor] = Field([], alias="childFactorsInModule")

class RatingModel(Base):
    name: str
    label: str
    template: Template
    template_id: int = Field(..., alias="templateId")
    qualitative_factors: List[RatingFactor] = Field([], alias="qualitativeFactors")
    quantitative_factors: List[RatingFactor] = Field([], alias="quantitativeFactors")
    quantitative_module: List[RatingModule] = Field([], alias="quantitativeModule")
    qualitative_module: List[RatingModule] = Field([], alias="qualitativeModule")

class RatingFactorScore(Base):
    factor_value: FactorValue = Field(..., alias="factorValue")
    score_dirty: bool = Field(..., alias="scoreDirty")
    rating_instance_id: int = Field(..., alias="ratingInstanceID")
    rating_factor_name: str = Field(..., alias="ratingFactorName")

class RatingInstance(Base):
    rating_instance_front_end_id: str = Field(..., alias="ratingInstanceFrontEndId")
    customer_id: int = Field(..., alias="customerID")
    financials_period_id: int = Field(..., alias="financialsPeriodID")
    rating_model_id: int = Field(..., alias="ratingModelID")
    factor_attribute_map: Dict[str, RatingFactorAttribute] = Field({}, alias="factorAttributeMap")
    factors: List[RatingFactor] = Field([], alias="factors")
    quant_factors: List[RatingFactor] = Field([], alias="quantFactors")
    qualitative_factors: List[RatingFactor] = Field([], alias="qualitativeFactors")
    derived_factors: List[RatingFactor] = Field([], alias="derivedFactors")
    quant_factor_scores: List[RatingFactorScore] = Field([], alias="quantFactorScores")
    qualitative_factor_scores: List[RatingFactorScore] = Field([], alias="qualitativeFactorScores")
    derived_factor_scores: List[RatingFactorScore] = Field([], alias="derivedFactorScores")
    factor_scores_map: Dict[str, float] = Field({}, alias="factorScoresMap")
    factor_scores: List[RatingFactorScore] = Field([], alias="factorScores")
    workflow_action_id: int = Field(..., alias="workflowActionId")
    workflow_action_type: WorkflowActionType = Field(..., alias="workflowActionType")

    customer: Customer
    financials_period: 'FinancialsPeriod' = Field(..., alias="financialsPeriod")
    rating_model: RatingModel = Field(..., alias="ratingModel")
    workflow_action: WorkflowAction = Field(..., alias="workflowAction")


class FinancialsPeriod(Base):
    year: int
    month: int
    date: int
    type: str  # actuals or other types

# Enum for StatementType
class StatementType(Enum):
    BS = "bs"
    PNL = "pnl"
    CASHFLOW = "cashflow"
    OTHER = "other"
class LineItemMetaSchema(BaseModel):
    id: Optional[int] = None
    template_id: int = Field(..., alias="templateId")
    fin_statement_type: StatementType = Field(..., alias="finStatementType")
    header: bool
    formula: str
    type: str
    label: str
    name: str
    lag_months: int = Field(..., alias="lagMonths")
    display: bool
    order_no: int = Field(..., alias="orderNo")
    display_order_no: int = Field(..., alias="displayOrderNo")
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")


# Pydantic schema
# class FinancialStatementSchema(BaseModel):
#     id: Optional[int] = None
#     actuals: bool
#     projections: bool
#     audit_type: str
#     standalone: bool
#     consolidated: bool
#     financials_period_id: int
#     customer_id: int
#     template_id: int
#     workflow_action_id: int
#     workflow_action_type: WorkflowActionType = Field(default=WorkflowActionType.DRAFT)
#     is_dirty: bool = Field(default=True)
#     preferred_statement: bool
#     source_of_lag_variables: Optional[int] = None
#     created_at: Optional[datetime] = None
#     updated_at: Optional[datetime] = None



# You might also want to create a schema for creating a new financial statement
class FinancialStatementCreate(BaseModel):
    actuals: bool
    projections: bool
    audit_type: str
    standalone: bool
    consolidated: bool
    financials_period_id: int
    customer_id: int
    template_id: int
    workflow_action_id: int
    workflow_action_type: WorkflowActionType = Field(default=WorkflowActionType.DRAFT)
    preferred_statement: bool
    source_of_lag_variables: Optional[int] = None





# Pydantic schema
class LineItemValueSchema(BaseModel):
    financial_statement_id: int
    line_item_meta_id: str
    value: Optional[float] = None

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

# Pydantic schema for creating/updating a LineItemValue
class LineItemValueCreate(BaseModel):
    financial_statement_id: int
    line_item_meta_id: str
    value: Optional[float] = None

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
class FinancialStatement(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    actuals: Optional[bool]
    projections: Optional[bool]
    audit_type: Optional[str]
    standalone: Optional[bool]
    consolidated: Optional[bool]
    financials_period_year: int
    financials_period_month: int
    financials_period_date: int
    customer_id: UUID
    template_id: UUID
    workflow_action_id: UUID
    workflow_action_type: WorkflowActionType = Field(default=WorkflowActionType.DRAFT)
    is_dirty: bool = Field(default=True)
    preferred_statement: Optional[bool] = None
    source_of_lag_variables: Optional[int] = None
    # class Config:
    #     orm_mode = True
    #     allow_population_by_field_name = True
class SpreadingStatementProperties(BaseModel):
    statement_type: str
    dates :List[str]

class MultiStatement(BaseModel):
    statement_1:UUID
    statement_2:Optional[UUID]=None
    statement_3:Optional[UUID]=None
    statement_4:Optional[UUID]=None
    statement_5:Optional[UUID]=None
    statement_6:Optional[UUID]=None
    
class SpreadingLineItems(MultiStatement):
    # spreading_statement_properties_id: UUID = Field(..., description="The unique identifier template into which it is being mapped")
    # spreading_statement_properties: SpreadingStatementProperties

    order_no:int
    template_id: UUID = Field(..., description="The unique identifier template into which it is being mapped")
    template_financial_item_id: Optional[UUID] = Field(...,description="Link to statmeent meta information")
    formula:Optional[str]=None
    template_financial_line_item_name:str
    template_label :Optional[str ]=Field(default=None)
    value_1:Optional[float]=None
    value_2:Optional[float]=None
    value_3:Optional[float]=None
    value_4:Optional[float]=None
    value_5:Optional[float]=None
    value_6:Optional[float]=None


class UpdatedValue(BaseModel):
    statement_id: str
    template_financial_item_id: str
    template_financial_line_item_name: str
    old_value: float
    new_value: float


