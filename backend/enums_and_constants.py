import enum


class WorkflowStage(enum.Enum):
    MAKER = "maker"
    CHECKER = "checker"
    APPROVER = "approver"

class ActionRight(enum.Enum):
    CREATE = "create"
    EDIT = "edit"
    DELETE = "delete"
    VIEW = "view"
    COMMENT = "comment"


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