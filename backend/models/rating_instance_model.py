from models.base import Base
from enums_and_constants import WorkflowStage


from sqlalchemy import JSON, UUID, Boolean, Column, Enum as SQLAlchemyEnum, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


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
    overall_status = Column(SQLAlchemyEnum(WorkflowStage), nullable=False, default=WorkflowStage.MAKER)
    maker_approved = Column(Boolean, nullable=False, default=False)
    checker_approved = Column(Boolean, nullable=False, default=False)
    approver_approved = Column(Boolean, nullable=False, default=False)

    customer = relationship("Customer")
    rating_model = relationship("RatingModel")
    financial_statement = relationship("FinancialStatement")
    workflow_actions = relationship("WorkflowAction",back_populates='rating_instance')

    @property
    def current_workflow_action(self):
        """Get the most recent workflow action"""
        return max(self.workflow_actions, key=lambda x: x.action_count_customer_level) if self.workflow_actions else None


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
