from enums_and_constants import RejectionFlow, WorkflowStage
from models.base import Base


from sqlalchemy import JSON, UUID, Boolean, Column, Enum as SQLAlchemyEnum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class PolicyRule(Base):
    __tablename__ = 'policy_rule'

    business_unit_id = Column(UUID, ForeignKey('businessunit.id'), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    is_active = Column(Boolean, default=True)

    # Relationships
    workflow_stages = relationship("WorkflowStageConfig")
    business_unit = relationship("BusinessUnit", lazy='joined')


class WorkflowStageConfig(Base):
    __tablename__ = 'workflow_stage_config'

    policy_id = Column(UUID, ForeignKey('policy_rule.id'), nullable=False)
    stage = Column(SQLAlchemyEnum(WorkflowStage), nullable=False)
    min_count = Column(Integer, nullable=False, default=1)
    allowed_roles = Column(JSON, nullable=False)  # List of role IDs that can perform this stage
    rights = Column(JSON, nullable=False)  # List of ActionRights
    order_in_stage = Column(Integer, nullable=False, default=1)  # For multiple approvers

    # For Approver stage
    is_sequential = Column(Boolean, default=True)
    rejection_flow = Column(SQLAlchemyEnum(RejectionFlow), default=RejectionFlow.TO_MAKER)

    policy = relationship("PolicyRule", back_populates="workflow_stages")