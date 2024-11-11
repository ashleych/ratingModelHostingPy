from enums_and_constants import ActionRight, WorkflowStage
from models.base import Base


from sqlalchemy import UUID, Boolean, Column, Enum as SQLAlchemyEnum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class WorkflowAction(Base):
    __tablename__ = 'workflowaction'

    workflow_cycle_id=Column(UUID, nullable=False)
    customer_id = Column(UUID, nullable=False)
    action_count_customer_level = Column(Integer)

    user_id = Column(UUID, ForeignKey('user.id'))
    description=Column(String)
    action_type = Column(SQLAlchemyEnum(ActionRight), nullable=False, default=ActionRight.VIEW)
    workflow_stage = Column(SQLAlchemyEnum(WorkflowStage), nullable=False, default=WorkflowStage.MAKER)
    preceding_action_id = Column(UUID, ForeignKey('workflowaction.id'))
    succeeding_action_id = Column(UUID, ForeignKey('workflowaction.id'))
    # rating_instance_id_received = Column(UUID(as_uuid=True), ForeignKey('ratinginstance.id'), nullable=True)
    rating_instance_id = Column(UUID(as_uuid=True), ForeignKey('ratinginstance.id'), nullable=True)
    policy_rule_id = Column(UUID(as_uuid=True), ForeignKey('policy_rule.id'), nullable=True)
    head = Column(Boolean,default=True)

    rating_instance = relationship("RatingInstance", back_populates="workflow_actions")  # not workflow_actions
    policy_rule = relationship("PolicyRule")  
    user = relationship("User")  