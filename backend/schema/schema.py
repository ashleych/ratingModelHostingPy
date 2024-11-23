from typing import Optional, Dict, Any
from ctypes import Union
from pydantic import BaseModel, Field, ConfigDict, validator
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, UUID4
from typing import List, Optional
from datetime import datetime
from enum import Enum
from enums_and_constants import ERROR_MESSAGES, WorkflowErrorCode, WorkflowStage, ActionRight, RejectionFlow

from enums_and_constants import AttributeType
from enums_and_constants import FactorType
from enums_and_constants import FactorInputSource


class BaseSchema(BaseModel):
    id: Optional[UUID] = Field(None, description="Unique identifier")
    created_at: Optional[datetime] = Field(None, description="Creation datetime")
    updated_at: Optional[datetime] = Field(None, description="Update datetime")
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True,extra='allow')


class User(BaseSchema):

    # id = Column(UUID, primary_key=True)
    name: Optional[str] = None
    email: str
    role: Optional[List[str|UUID]] = None
    password: str


class FactorValue(BaseModel):
    """Embedded struct for factor values"""

    raw_value_text: Optional[str] = None
    raw_value_float: Optional[float] = None
    score: Optional[float] = None

    # @validator('raw_value_float')
    # def validate_float_value(cls, v):
    #     if v is not None and (not isinstance(v, (int, float)) or not -float('inf') <= v <= float('inf')):
    #         raise ValueError('raw_value_float must be a valid number')
    #     return v

    # @validator('score')
    # def validate_score(cls, v):
    #     if v is not None and (not isinstance(v, (int, float)) or not -float('inf') <= v <= float('inf')):
    #         raise ValueError('score must be a valid number')
    #     return v


# class FactorValue(BaseModel):
#     raw_value_text: str = Field(..., alias="rawValueText")
#     raw_value_float: float = Field(..., alias="rawValueFloat")
#     score: float


class TemplateSourceCSV(BaseSchema):
    source_path: Optional[str | UUID] = None


class Template(BaseSchema):
    name: str
    description: Optional[str] = None
    template_source_csv: Optional[TemplateSourceCSV] = None
    template_source_csv_id: Optional[UUID ] = None


class PolicyRuleBase(BaseSchema):
    name: str
    business_unit_id: UUID4
    description: Optional[str] = None
    sequential_approval: bool = True
    rejection_flow: RejectionFlow = RejectionFlow.TO_MAKER

# class WorkflowCycle(BaseSchema):




class WorkflowAction(BaseSchema):
    workflow_cycle_id: UUID = Field(..., alias="workflow_cycle_id")

    customer_id: UUID = Field(..., alias="customer_id")
    action_count_customer_level: int = Field(..., alias="action_count_customer_level")
    user_id: UUID = Field(...)
    workflow_stage: WorkflowStage = Field(..., alias="workflow_stage")
    action_type: ActionRight = Field(..., alias="action_type")
    rating_instance_id: Optional[UUID] = None
    # rating_instance_id_received:Optional[UUID]=None
    # rating_instance_id_cloned:Optional[UUID]=None
    description: Optional[str] = None
    preceding_action_id: Optional[UUID] = Field(None, alias="preceding_action_id")
    succeeding_action_id: Optional[UUID] = Field(None, alias="succeeding_action_id")
    head: bool
    is_stale: bool
    policy_rule_id: UUID

    def clone(self, user_id=None, action_type=None,stage=None):
        if self.head:
            self.head = False
            self.is_stale= True
            cloned_wf = {
                "workflow_cycle_id": self.workflow_cycle_id,
                "customer_id": self.customer_id,
                "action_count_customer_level": self.action_count_customer_level + 1,
                "user_id": user_id if user_id else self.user_id,
                "action_type": action_type if action_type else self.action_type,
                "rating_instance_id": self.rating_instance_id,
                "workflow_stage":stage if stage else self.workflow_stage,
                "description": None,
                "preceding_action_id": self.id,
                "succeeding_action_id": None,
                "is_stale": False,
                "policy_rule_id": self.policy_rule_id,
                "head": True,
            }
            return cloned_wf
        else:
            raise ValueError("Unable to clone the workflow as it is not the head")


    def available_next_steps(self):
        if (self.workflow_stage==WorkflowStage.MAKER) & (self.action_type==ActionRight.SUBMIT):
            return WorkflowStage.CHECKER
        if (self.workflow_stage==WorkflowStage.CHECKER) & (self.action_type==ActionRight.SUBMIT):
            return WorkflowStage.APPROVER
        
        


class WorkflowActionCreate(BaseModel):
    workflow_cycle_id: UUID = Field(...)
    id: UUID
    customer_id: UUID
    action_count_customer_level: int
    user_id: UUID
    workflow_stage: WorkflowStage
    action_type:ActionRight 
    description: Optional[str] = None
    rating_instance_id: Optional[UUID] = None
    preceding_action_id: Optional[UUID] = None
    succeeding_action_id: Optional[UUID] = None
    head: bool
    is_stale: bool

    model_config = ConfigDict(from_attributes=True)


class BusinessUnit(BaseSchema):
    name: str


class MasterRatingScale(BaseSchema):
    rating_grade: str = Field(..., alias="ratingGrade")
    pd: float


class Customer(BaseSchema):
    customer_name: str = Field(..., alias="customerName")
    cif_number: str = Field(..., alias="cifNumber")
    group_name: str = Field(..., alias="groupName")
    business_unit: BusinessUnit = Field(..., alias="businessUnit")
    business_unit_id: str = Field(..., alias="businessUnitId")
    relationship_type: str = Field(..., alias="relationshipType")
    internal_risk_rating: str = Field(..., alias="internalRiskRating")
    master_rating_scale: MasterRatingScale = Field(..., alias="masterRatingScale")
    # workflow_action_id: Optional[int] = Field(None, alias="workflowActionId")
    # workflow_action: WorkflowAction = Field(..., alias="workflowaction")
    # workflow_action_type: WorkflowActionType = Field(..., alias="workflowActionType")


class RatingFactorAttribute(BaseSchema):
    rating_factor_name: str = Field(..., alias="ratingFactorName")
    rating_model_id: int = Field(..., alias="ratingModelID")
    name: str
    label: str
    attribute_type: AttributeType = Field(..., alias="attributeType")
    bin_start: Optional[float] = Field(None, alias="binStart")
    bin_end: Optional[float] = Field(None, alias="binEnd")
    score: float


class RatingFactor(BaseSchema):
    name: str
    label: str
    weightage: float
    parent_factor: Optional["RatingFactor"] = Field(None, alias="parentFactor")
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
    child_factors_in_module: List[RatingFactor] = Field(
        [], alias="childFactorsInModule"
    )


class RatingModel(BaseSchema):
    name: str
    label: str
    template: Template
    template_id: UUID = Field(..., alias="template_id")
    qualitative_factors: List[RatingFactor] = Field([], alias="qualitativeFactors")
    quantitative_factors: List[RatingFactor] = Field([], alias="quantitativeFactors")
    quantitative_module: List[RatingModule] = Field([], alias="quantitativeModule")
    qualitative_module: List[RatingModule] = Field([], alias="qualitativeModule")

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class RatingFactorScore(BaseSchema):
    """Base schema with common attributes"""

    raw_value_text: Optional[str] = None
    raw_value_float: Optional[float] = None
    score: Optional[float] = None
    # factor_value: FactorValue
    score_dirty: bool = True
    rating_instance_id: UUID
    rating_factor_id: UUID


class RatingFactorScoreCreate(BaseModel):
    raw_value_text: Optional[str] = None
    raw_value_float: Optional[float] = None
    score: Optional[float] = None
    score_dirty: bool = True
    rating_instance_id: UUID
    rating_factor_id: UUID


class RatingInstance(BaseSchema):
    """Base Pydantic model for RatingInstance data validation"""

    customer_id: UUID
    financial_statement_id: UUID
    rating_model_id: UUID
    # workflow_action_id: Optional[UUID] = None

    inputs_completion_status: bool = False
    incomplete_financial_information: bool = False
    missing_financial_fields: Optional[Any] = None
    overall_score: Optional[float] = None
    overall_rating: Optional[str] = None
    overall_status: WorkflowStage = WorkflowStage.MAKER

    model_config = ConfigDict(from_attributes=True)

    def clone(self):
        cloned_rating_instance = {
            "customer_id": self.customer_id,
            "rating_model_id": self.rating_model_id,
            "financial_statement_id": self.financial_statement_id,
            "inputs_completion_status": self.inputs_completion_status,
            "incomplete_financial_information": self.incomplete_financial_information,
            "missing_financial_fields": self.missing_financial_fields,
            "overall_score": self.overall_score,
            "overall_rating": self.overall_rating,
            "overall_status": self.overall_status,
        }
        return cloned_rating_instance


class RatingInstanceCreate(BaseModel):
    """Base Pydantic model for RatingInstance data validation"""

    id: UUID
    customer_id: UUID
    financial_statement_id: UUID
    rating_model_id: UUID
    # workflow_action_id: Optional[UUID] = None

    inputs_completion_status: bool = False
    incomplete_financial_information: bool = False
    missing_financial_fields: Optional[Any] = None
    workflow_action_id:UUID 
    overall_score: Optional[float] = None
    overall_rating: Optional[str] = None
    overall_status: WorkflowStage = WorkflowStage.MAKER

    model_config = ConfigDict(from_attributes=True)


class FinancialsPeriod(BaseSchema):
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
    workflow_action_type: WorkflowStage = Field(default=WorkflowStage.MAKER)
    preferred_statement: bool
    source_of_lag_variables: Optional[int] = None


# Pydantic schema
class LineItemValueSchema(BaseModel):
    financial_statement_id: int
    line_item_meta_id: str
    value: Optional[float] = None


class LineItemValueCreate(BaseModel):
    financial_statement_id: int
    line_item_meta_id: str
    value: Optional[float] = None


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
    # workflow_action_id: UUID
    # workflow_action_type: WorkflowActionType = Field(default=WorkflowActionType.DRAFT)
    is_dirty: bool = Field(default=True)
    preferred_statement: Optional[bool] = None
    source_of_lag_variables: Optional[int] = None
    # class Config:
    #     orm_mode = True
    #     allow_population_by_field_name = True


class SpreadingStatementProperties(BaseModel):
    statement_type: str
    dates: List[str]


class MultiStatement(BaseModel):
    statement_1: UUID
    statement_2: Optional[UUID] = None
    statement_3: Optional[UUID] = None
    statement_4: Optional[UUID] = None
    statement_5: Optional[UUID] = None
    statement_6: Optional[UUID] = None


class SpreadingLineItems(MultiStatement):
    # spreading_statement_properties_id: UUID = Field(..., description="The unique identifier template into which it is being mapped")
    # spreading_statement_properties: SpreadingStatementProperties

    order_no: int
    template_id: UUID = Field(
        ..., description="The unique identifier template into which it is being mapped"
    )
    template_financial_item_id: Optional[UUID] = Field(
        ..., description="Link to statmeent meta information"
    )
    formula: Optional[str] = None
    template_financial_line_item_name: str
    template_label: Optional[str] = Field(default=None)
    value_1: Optional[float] = None
    value_2: Optional[float] = None
    value_3: Optional[float] = None
    value_4: Optional[float] = None
    value_5: Optional[float] = None
    value_6: Optional[float] = None


class UpdatedValue(BaseModel):
    statement_id: str
    template_financial_item_id: str
    template_financial_line_item_name: str
    old_value: float
    new_value: float


class CustomerHistory(BaseModel):
    workflow_actions: List[WorkflowAction] = Field([], alias="workFlowActions")
    customers: List[Customer] = Field([], alias="customers")
    rating_instances: List[RatingInstance] = Field([], alias="ratingInstances")


# --- Pydantic Models ---
class WorkflowStageConfigCreate(BaseModel):
    stage: WorkflowStage
    min_count: int
    allowed_roles: List[str]
    rights: List[ActionRight]
    order_in_stage: int = 1
    is_sequential: Optional[bool] = True
    rejection_flow: Optional[RejectionFlow] = RejectionFlow.TO_MAKER


class PolicyRulesCreate(BaseModel):
    business_unit_id: UUID
    name: str
    description: Optional[str]
    workflow_stages: List[WorkflowStageConfigCreate]


class PolicyRulesResponse(BaseModel):
    id: UUID
    business_unit_id: UUID
    name: str
    description: Optional[str]
    is_active: bool
    workflow_stages: List[Dict]
    created_at: datetime
    updated_at: datetime


# class WorkflowStage(str, Enum):
#     MAKER = "maker"
#     CHECKER = "checker"
#     APPROVER = "approver"

# class ActionRight(str, Enum):
#     CREATE = "create"
#     EDIT = "edit"
#     DELETE = "delete"
#     VIEW = "view"
#     COMMENT = "comment"

# class RejectionFlow(str, Enum):
#     TO_MAKER = "to_maker"
#     TO_CHECKER = "to_checker"
#     TO_PREVIOUS_STAGE = "to_previous_stage"


class WorkflowStageConfigBase(BaseModel):
    stage: WorkflowStage
    allowed_roles: List[str]
    rights: List[ActionRight]
    min_count: int = 1


class WorkflowStageConfigResponse(WorkflowStageConfigBase):
    id: UUID4
    policy_id: UUID4
    created_at: datetime
    updated_at: datetime


class PolicyRuleCreate(PolicyRuleBase):
    workflow_stages: List[WorkflowStageConfigCreate]


class PolicyRuleUpdate(PolicyRuleBase):
    workflow_stages: List[WorkflowStageConfigCreate]


class PolicyRuleResponse(PolicyRuleBase):
    is_active: bool
    workflow_stages: List[WorkflowStageConfigResponse]
    created_by: UUID4


class RatingModelApplicabilityRulesCreate(BaseSchema):
    rating_model_id: UUID
    business_unit_id: UUID

    rating_model: RatingModel
    business_unit: BusinessUnit


class RatingModelApplicabilityRules(BaseSchema):
    rating_model_id: UUID
    business_unit_id: UUID

    rating_model: RatingModel
    business_unit: BusinessUnit


class WorkflowError(Exception):
    def __init__(
        self,
        code: WorkflowErrorCode,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message or ERROR_MESSAGES[code]
        self.details = details
        super().__init__(self.message)


# Response model for API
class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
