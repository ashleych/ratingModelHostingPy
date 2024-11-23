from typing import List
from uuid import uuid4
from enums_and_constants import AcceptFlow, ActionRight, EditFlow, RejectionFlow, WorkflowStage
from models.base import Base


from sqlalchemy import JSON, UUID, Boolean, Column, Enum as SQLAlchemyEnum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Session, relationship

from models.models import Role, User


# class RatingAccessRule(Base):
#     __tablename__ = 'rating_access_rules'

#     id = Column(UUID, primary_key=True, default=uuid4)
#     policy_id = Column(UUID, ForeignKey('policy_rule.id'), nullable=False)
#     role_name = Column(String, nullable=False)  # Store role name instead of role_id
#     workflow_stage = Column(SQLAlchemyEnum(WorkflowStage), nullable=False)
#     action_rights = Column(ARRAY(SQLAlchemyEnum(ActionRight)), nullable=False)

#     # Configuration
#     approval_order = Column(Integer, nullable=True)
#     is_mandatory = Column(Boolean, default=False)
#     rejection_flow = Column(SQLAlchemyEnum(RejectionFlow), default=RejectionFlow.TO_MAKER)
#     edit_flow = Column(SQLAlchemyEnum(EditFlow), default=EditFlow.TO_PREVIOUS_STAGE)
#     accept_flow = Column(SQLAlchemyEnum(AcceptFlow), default=AcceptFlow.TO_NEXT_STAGE)

#     # Relationships
#     policy = relationship("PolicyRule")

#     @classmethod
#     def get_user_access(cls, db: Session, policy_id: UUID, user_id: UUID, workflow_stage: WorkflowStage) -> List['RatingAccessRule']:
#         """Get access rules for a user in a specific stage"""
#         # First get the user's roles
#         user = db.query(User).filter(User.id == user_id).first()

#         if not user or not user.role:
#             return []

#         # Get access rules that match user's roles
#         return (
#             db.query(cls)
#             .filter(
#                 cls.policy_id == policy_id,
#                 cls.workflow_stage == workflow_stage,
#                 cls.role_name.in_(user.role)  # user.role is the JSON array of role names
#             )
#             .all()
#         )
class RatingAccessRule(Base):


    __tablename__ = 'rating_access_rules'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    policy_id = Column(UUID(as_uuid=True), ForeignKey('policy_rule.id'), nullable=False)
    role_name = Column(String, nullable=False)
    workflow_stage = Column(SQLAlchemyEnum(WorkflowStage), nullable=False)
    action_rights = Column(ARRAY(SQLAlchemyEnum(ActionRight)), nullable=False)

    # Configuration
    approval_order = Column(Integer, nullable=True)
    is_mandatory = Column(Boolean, default=False)
    rejection_flow = Column(SQLAlchemyEnum(RejectionFlow), default=RejectionFlow.TO_MAKER)
    edit_flow = Column(SQLAlchemyEnum(EditFlow), default=EditFlow.TO_PREVIOUS_STAGE)
    accept_flow = Column(SQLAlchemyEnum(AcceptFlow), default=AcceptFlow.TO_NEXT_STAGE)

    # Relationship back to policy
    policy = relationship("PolicyRule", back_populates="access_rules")

    @classmethod
    def get_user_access(cls, db: Session, policy_id: UUID, user_id: UUID, workflow_stage: WorkflowStage) -> List['RatingAccessRule']:
        """Get access rules for a user in a specific stage"""
        # First get the user's roles
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.role:
            return []

        # Get access rules that match user's roles
        return (
            db.query(cls)
            .filter(
                cls.policy_id == policy_id,
                cls.workflow_stage == workflow_stage,
                cls.role_name.in_(user.role)
            )
            .all()
        )

    def get_allowed_actions(self) -> List[ActionRight]:
        """Get list of allowed actions"""
        return self.action_rights if self.action_rights else []


# class PolicyRule(Base):
#     __tablename__ = 'policy_rule'

#     business_unit_id = Column(UUID, ForeignKey('businessunit.id'), nullable=False)
#     name = Column(String, nullable=False)
#     description = Column(String)
#     is_active = Column(Boolean, default=True)

#     # Relationships
#     # workflow_stages = relationship("WorkflowStageConfig")
#     business_unit = relationship("BusinessUnit", lazy='joined')


# class WorkflowStageConfig(Base):
#     __tablename__ = 'workflow_stage_config'

#     policy_id = Column(UUID, ForeignKey('policy_rule.id'), nullable=False)
#     stage = Column(SQLAlchemyEnum(WorkflowStage), nullable=False)
#     min_count = Column(Integer, nullable=False, default=1)
#     allowed_roles = Column(JSON, nullable=False)  # List of role IDs that can perform this stage
#     rights = Column(JSON, nullable=False)  # List of ActionRights
#     order_in_stage = Column(Integer, nullable=False, default=1)  # For multiple approvers

#     # For Approver stage
#     is_sequential = Column(Boolean, default=True)
#     rejection_flow = Column(SQLAlchemyEnum(RejectionFlow), default=RejectionFlow.TO_MAKER)

#     policy = relationship("PolicyRule", back_populates="workflow_stages")

class PolicyRule(Base):
    __tablename__ = 'policy_rule'

    business_unit_id = Column(UUID, ForeignKey('businessunit.id'), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    is_active = Column(Boolean, default=True)

    # Relationships
    business_unit = relationship("BusinessUnit", lazy='joined')
    access_rules = relationship("RatingAccessRule", back_populates="policy")

    def get_stage_rules(self, stage: WorkflowStage) -> List[RatingAccessRule]:
        """Get all access rules for a specific stage"""
        return [rule for rule in self.access_rules if rule.workflow_stage == stage]

    def get_mandatory_roles(self, stage: WorkflowStage) -> List[str]:
        """Get mandatory roles for a stage"""
        return [
            rule.role_name 
            for rule in self.access_rules 
            if rule.workflow_stage == stage and rule.is_mandatory
        ]

    def can_user_access_stage(self, user: User, stage: WorkflowStage) -> bool:
        """Check if user has any role that can access this stage"""
        allowed_roles = {
            rule.role_name 
            for rule in self.access_rules 
            if rule.workflow_stage == stage
        }
        return any(role in allowed_roles for role in user.role)
