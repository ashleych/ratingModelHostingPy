import enum
from enum import Enum
from typing import Dict


class WorkflowStage(enum.Enum):
    MAKER = "maker"
    CHECKER = "checker"
    APPROVER = "approver"
    APPROVED="approved"

    @classmethod
    def get_stage_order(cls) -> Dict[str, int]:
        """Get the order of stages in the workflow"""
        return {
            cls.MAKER.value: 1,
            cls.CHECKER.value: 2,
            cls.APPROVER.value: 3,
            cls.APPROVED.value: 4
        }

    def __lt__(self, other):
        if not isinstance(other, WorkflowStage):
            return NotImplemented
        return self.get_stage_order()[self.value] < self.get_stage_order()[other.value]

    @property
    def order(self) -> int:
        """Get numerical order of this stage"""
        return self.get_stage_order()[self.value]

    def is_before(self, other: 'WorkflowStage') -> bool:
        """Check if this stage comes before another stage"""
        return self.order < other.order

    def is_after(self, other: 'WorkflowStage') -> bool:
        """Check if this stage comes after another stage"""
        return self.order > other.order

class ActionRight(enum.Enum):
    CREATE = "create"
    EDIT = "edit"
    DELETE = "delete"
    VIEW = "view"
    COMMENT = "comment"
    TRANSFER='transfer'
    APPROVE='approve'
    REJECT='reject'
    # SUBMIT='submit'

    @classmethod
    def from_string(cls, value: str) -> 'ActionRight':
        """Convert string value to enum value safely"""
        value_map = {
            "CREATE": cls.CREATE,
            "EDIT": cls.EDIT,
            "DELETE": cls.DELETE,
            "APPROVE": cls.APPROVE,
            "VIEW": cls.VIEW,
            "COMMENT": cls.COMMENT,
            "TRANSFER": cls.TRANSFER,
            "REJECT": cls.REJECT,
            # "SUBMIT": cls.SUBMIT
        }
        return value_map.get(value.upper(),cls.VIEW)
    
class AcceptFlow(enum.Enum):
    TO_MAKER = "to_maker"
    TO_CHECKER = "to_checker"
    TO_PREVIOUS_STAGE = "to_previous_stage"
    TO_NEXT_STAGE = "to_next_stage"

    @classmethod
    def from_string(cls, value: str):
        """Convert form string value to enum value safely"""
        value_map = {
            "TO_MAKER": cls.TO_MAKER,
            "TO_CHECKER": cls.TO_CHECKER,
            "TO_PREVIOUS_STAGE": cls.TO_PREVIOUS_STAGE
        }
        return value_map.get(value, cls.TO_PREVIOUS_STAGE) 

class EditFlow(enum.Enum):
    TO_MAKER = "to_maker"
    TO_CHECKER = "to_checker"
    TO_PREVIOUS_STAGE = "to_previous_stage"

    @classmethod
    def from_string(cls, value: str):
        """Convert form string value to enum value safely"""
        value_map = {
            "TO_MAKER": cls.TO_MAKER,
            "TO_CHECKER": cls.TO_CHECKER,
            "TO_PREVIOUS_STAGE": cls.TO_PREVIOUS_STAGE
        }
        return value_map.get(value, cls.TO_PREVIOUS_STAGE) #default to previous stage

class RejectionFlow(enum.Enum):
    TO_MAKER = "to_maker"
    TO_CHECKER = "to_checker"
    TO_PREVIOUS_STAGE = "to_previous_stage"

    @classmethod
    def from_string(cls, value: str):
        """Convert form string value to enum value safely"""
        value_map = {
            "TO_MAKER": cls.TO_MAKER,
            "TO_CHECKER": cls.TO_CHECKER,
            "TO_PREVIOUS_STAGE": cls.TO_PREVIOUS_STAGE
        }
        return value_map.get(value, cls.TO_MAKER)  # Default to TO_MAKER if invalid


# class WorkflowStatus(enum.Enum):
#     INITIATED = 'initiated'
#     DRAFT = "draft"
#     GENERATED = "generated"
#     SUBMITTED = "submitted"
#     EDIT = "edited"
#     UNDER_REVIEW = "under_review"
#     REVIEWED = "reviewed"
#     APPROVED = "approved"
#     REJECTED = "rejected"


class AttributeType(str, Enum):
    BIN = "bin"
    LOOKUP = "lookup"


class FactorType(str, Enum):
    QUALITATIVE = "qualitative"
    OVERALLSCORE = "overallScore"
    QUANTITATIVE = "quantitative"


class FactorInputSource(str, Enum):
    USER_INPUT = "user_input"
    FINANCIAL_STATEMENT = "financial_statement"
    DERIVED = "derived"


# Define error codes
class WorkflowErrorCode(Enum):
    POLICY_RULE_NOT_FOUND = "POLICY_RULE_NOT_FOUND"
    UNAUTHORIZED_ROLE = "UNAUTHORIZED_ROLE"
    WORKFLOW_EXISTS = "WORKFLOW_EXISTS"
    NOT_HEAD_ACTION = "NOT_HEAD_ACTION"
    ALREADY_SUBMITTED = "ALREADY_SUBMITTED"
    MISSING_MAKER_STAGE = "MISSING_MAKER_STAGE"
    UNAUTHORIZED_ACTION = "UNAUTHORIZED_ACTION"
    STATEMENT_NOT_FOUND = "STATEMENT_NOT_FOUND"
    WORKFLOW_CREATION_FAILED="WORKFLOW_CREATION_FAILED"


# Define error messages
ERROR_MESSAGES = {
    WorkflowErrorCode.POLICY_RULE_NOT_FOUND: "No policy rule found for customer {cif_number}",
    WorkflowErrorCode.UNAUTHORIZED_ROLE: "User does not have required maker role for this policy",
    WorkflowErrorCode.WORKFLOW_EXISTS: "Workflow already exists for this customer",
    WorkflowErrorCode.NOT_HEAD_ACTION: "Cannot perform action: not the head workflow anymore",
    WorkflowErrorCode.ALREADY_SUBMITTED: "Workflow has already been submitted",
    WorkflowErrorCode.MISSING_MAKER_STAGE: "No maker stage configuration found for this policy",
    WorkflowErrorCode.UNAUTHORIZED_ACTION: "User is not authorized to perform {action} action",
    WorkflowErrorCode.STATEMENT_NOT_FOUND: "No financial statement found for customer {customer_id} for year {year}",
    WorkflowErrorCode.WORKFLOW_CREATION_FAILED: "Workflow unable to be created for {customer_id} "
}