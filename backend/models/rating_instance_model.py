from uuid import uuid4
from models.base import Base
from enums_and_constants import WorkflowStage


from sqlalchemy import JSON, UUID, Boolean, Column, Enum as SQLAlchemyEnum, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship,Session
from schema import schema

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
    # overall_status = Column(SQLAlchemyEnum(WorkflowStage), nullable=False, default=WorkflowStage.MAKER)
    maker_approved = Column(Boolean, nullable=False, default=False)
    checker_approved = Column(Boolean, nullable=False, default=False)
    approver_approved = Column(Boolean, nullable=False, default=False)

    customer = relationship("Customer")
    rating_model = relationship("RatingModel")
    financial_statement = relationship("FinancialStatement")
    workflow_actions = relationship("WorkflowAction",back_populates='rating_instance')

    # @property
    # def current_workflow_action(self):
    #     """Get the most recent workflow action"""
    #     return max(self.workflow_actions, key=lambda x: x.action_count_customer_level) if self.workflow_actions else None
    def clone_rating_instance(self,db: Session) -> "RatingInstance":
        # Validate using Pydantic schema
        new_instance_db = RatingInstance(
            id=uuid4(),
            customer_id=self.customer_id,
            financial_statement_id=self.financial_statement_id,
            rating_model_id=self.rating_model_id,
            # workflow_action_id=new_workflow_step.id,
            # overall_status=new_workflow_step.workflow_stage,
            incomplete_financial_information=self.incomplete_financial_information,
            missing_financial_fields=self.missing_financial_fields,
            overall_score=self.overall_score,
            overall_rating=self.overall_rating
        )

        # new_instance_db = RatingInstance(**instance_data.model_dump())
        db.add(new_instance_db)
        db.flush()
        new_instance=schema.RatingInstance(**new_instance_db.__dict__)
        if new_instance.id is None:
            raise ValueError("new_instance ID cannot be None when performing action")

        rf_scores_db= db.query(RatingFactorScore).filter(RatingFactorScore.rating_instance_id == self.id).all()

        rf_scores= [schema.RatingFactorScore(**rf.__dict__) for rf in rf_scores_db]
            
        # Clone and validate factor scores
        for score in rf_scores:
            score_data = schema.RatingFactorScoreCreate(
                rating_instance_id=new_instance.id,
                rating_factor_id=score.rating_factor_id,
                    raw_value_text=score.raw_value_text,
                    raw_value_float= score.raw_value_float,
                    score= score.score
                
            )
            new_score = RatingFactorScore(**score_data.model_dump())
            db.add(new_score)
            db.commit()
        return new_instance_db

    

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
