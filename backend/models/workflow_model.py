from typing import Optional
from enums_and_constants import ActionRight, WorkflowStage
from models.base import Base


from sqlalchemy import UUID, Boolean, Column, Enum as SQLAlchemyEnum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship,Session


# class WorkflowAction(Base):
#     __tablename__ = 'workflowaction'

#     workflow_cycle_id=Column(UUID, nullable=False)
#     customer_id = Column(UUID, nullable=False)
#     action_count_customer_level = Column(Integer)

#     user_id = Column(UUID, ForeignKey('user.id'))
#     description=Column(String)
#     action_type = Column(SQLAlchemyEnum(ActionRight), nullable=False, default=ActionRight.VIEW)
#     workflow_stage = Column(SQLAlchemyEnum(WorkflowStage), nullable=False, default=WorkflowStage.MAKER)
#     preceding_action_id = Column(UUID, ForeignKey('workflowaction.id'))
#     succeeding_action_id = Column(UUID, ForeignKey('workflowaction.id'))
#     # rating_instance_id_received = Column(UUID(as_uuid=True), ForeignKey('ratinginstance.id'), nullable=True)
#     rating_instance_id = Column(UUID(as_uuid=True), ForeignKey('ratinginstance.id'), nullable=True)
#     policy_rule_id = Column(UUID(as_uuid=True), ForeignKey('policy_rule.id'), nullable=True)
#     head = Column(Boolean,default=True)
#     is_stale= Column(Boolean,default= False)
#     rating_instance = relationship("RatingInstance", back_populates="workflow_actions")  # not workflow_actions
#     policy_rule = relationship("PolicyRule")  
#     user = relationship("User")  

#     def clone(self, user_id=None, action_type=None,stage=None,db:Session):
#         if self.head:
#             self.head = False
#             self.is_stale= True
#             cloned_wf = {
#                 "workflow_cycle_id": self.workflow_cycle_id,
#                 "customer_id": self.customer_id,
#                 "action_count_customer_level": self.action_count_customer_level + 1,
#                 "user_id": user_id if user_id else self.user_id,
#                 "action_type": action_type if action_type else self.action_type,
#                 "rating_instance_id": self.rating_instance_id,
#                 "workflow_stage":stage if stage else self.workflow_stage,
#                 "description": None,
#                 "preceding_action_id": self.id,
#                 "succeeding_action_id": None,
#                 "is_stale": False,
#                 "policy_rule_id": self.policy_rule_id,
#                 "head": True,
#             }
#             return cloned_wf
#         else:
#             raise ValueError("Unable to clone the workflow as it is not the head")
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import event

from enums_and_constants import AcceptFlow, ActionRight, WorkflowStage


from uuid import uuid4
from typing import List
from sqlalchemy import Column, ForeignKey, Boolean, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship,Session

from models.policy_rules_model import PolicyRule, RatingAccessRule

# Add methods to WorkflowAction
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
    is_stale= Column(Boolean,default= False)
    rating_instance = relationship("RatingInstance", back_populates="workflow_actions")  # not workflow_actions
    policy_rule = relationship("PolicyRule")  
    user = relationship("User")  
    # ... your existing fields ...

    def clone(self, db: Session, user_id=None, action_type=None, stage=None) -> 'WorkflowAction':
        """
        Clone the current workflow action and handle all database operations.
        Returns the new workflow action instance after committing to db.
        """
        if not self.head:
            raise ValueError("Unable to clone the workflow as it is not the head")

        try:
            # Start a nested transaction
            with db.begin_nested():
                # Update current workflow action
                self.head = False
                self.is_stale = True
                db.add(self)

                # Create new workflow action
                new_workflow = WorkflowAction(
                    id=uuid4(),
                    workflow_cycle_id=self.workflow_cycle_id,
                    customer_id=self.customer_id,
                    action_count_customer_level=self.action_count_customer_level + 1,
                    user_id=user_id if user_id else self.user_id,
                    action_type=action_type if action_type else self.action_type,
                    rating_instance_id=self.rating_instance_id,
                    workflow_stage=stage if stage else self.workflow_stage,
                    description=None,
                    preceding_action_id=self.id,
                    succeeding_action_id=None,
                    is_stale=False,
                    policy_rule_id=self.policy_rule_id,
                    head=True
                )
                db.add(new_workflow)

            # Commit the transaction
            db.commit()
            return new_workflow

        except Exception as e:
            db.rollback()
            raise ValueError(f"Failed to clone workflow action: {str(e)}")

    def get_next_stage(self) -> WorkflowStage:
        """Get the next workflow stage based on current stage"""
        stage_progression = {
            WorkflowStage.MAKER: WorkflowStage.CHECKER,
            WorkflowStage.CHECKER: WorkflowStage.APPROVER,
            WorkflowStage.APPROVER: WorkflowStage.APPROVED
        }
        return stage_progression.get(self.workflow_stage, self.workflow_stage)

    def submit(self, db: Session, user_id=None) -> 'WorkflowAction':
        """
        Submit the workflow action to the next stage.
        Returns the new workflow action after committing to db.
        """
        next_stage = self.get_next_stage()
        return self.clone(
            db=db,
            user_id=user_id,
            action_type=ActionRight.VIEW,
            stage=next_stage
        )

    @classmethod
    def get_active_workflow(cls, db: Session, rating_instance_id: UUID) -> Optional['WorkflowAction']:
        """Get the current active (head) workflow action for a rating instance"""
        return db.query(cls).filter(
            cls.rating_instance_id == rating_instance_id,
            cls.head == True,
            cls.is_stale == False
        ).first()





    def get_next_flow(self, db: Session, action: ActionRight) -> Optional[WorkflowStage]:
        """Determine next workflow stage based on action and policy"""
        current_rules = (
            db.query(RatingAccessRule)
            .filter(
                RatingAccessRule.policy_id == self.policy_rule_id,
                RatingAccessRule.workflow_stage == self.workflow_stage
            )
            .all()
        )
        
        if not current_rules:
            return None

        # Get the first applicable rule (you might want to add more specific logic)
        rule = current_rules[0]

        if action == ActionRight.SUBMIT:
            flow = rule.accept_flow
            if flow == AcceptFlow.TO_NEXT_STAGE:
                stages = [WorkflowStage.MAKER, WorkflowStage.CHECKER, WorkflowStage.APPROVER]
                current_idx = stages.index(self.workflow_stage)
                return stages[current_idx + 1] if current_idx < len(stages) - 1 else WorkflowStage.APPROVED
            return WorkflowStage[flow.value.upper()]
            
        elif action == ActionRight.EDIT:
            flow = rule.edit_flow
            return WorkflowStage[flow.value.upper()]
            
        return None

    def get_user_rights(self, db: Session, user_id: UUID) -> List[ActionRight]:
        """Get all allowed actions for user in current workflow stage"""
        access_rules = RatingAccessRule.get_user_access(
            db, 
            self.policy_rule_id, 
            user_id, 
            self.workflow_stage
        )
        all_actions = []
        for rule in access_rules:
            all_actions.extend(rule.action_rights)
        return list(set(all_actions))  # Remove duplicates

    def can_user_perform_action(self, db: Session, user_id: UUID, action: ActionRight) -> bool:
        """Check if user can perform specific action"""
        user_rights = self.get_user_rights(db, user_id)
        return action in user_rights       


