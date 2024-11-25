from typing import Optional, Tuple
from enums_and_constants import ActionRight, WorkflowStage
from models.base import Base


from sqlalchemy import (
    UUID,
    Boolean,
    Column,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Session


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
from sqlalchemy.orm import relationship, Session

from models.policy_rules_model import PolicyRule, RatingAccessRule
from models.rating_instance_model import RatingInstance


# Add methods to WorkflowAction
class WorkflowAction(Base):
    __tablename__ = "workflowaction"

    workflow_cycle_id = Column(UUID, nullable=False)
    customer_id = Column(UUID, nullable=False)
    action_count_customer_level = Column(Integer)

    user_id = Column(UUID, ForeignKey("user.id"))
    description = Column(String)
    action_type = Column(
        SQLAlchemyEnum(ActionRight), nullable=False, default=ActionRight.VIEW
    )
    workflow_stage = Column(
        SQLAlchemyEnum(WorkflowStage), nullable=False, default=WorkflowStage.MAKER
    )
    preceding_action_id = Column(UUID, ForeignKey("workflowaction.id"))
    succeeding_action_id = Column(UUID, ForeignKey("workflowaction.id"))
    # rating_instance_id_received = Column(UUID(as_uuid=True), ForeignKey('ratinginstance.id'), nullable=True)
    rating_instance_id = Column(
        UUID(as_uuid=True), ForeignKey("ratinginstance.id"), nullable=True
    )
    policy_rule_id = Column(
        UUID(as_uuid=True), ForeignKey("policy_rule.id"), nullable=True
    )
    head = Column(Boolean, default=True)
    is_stale = Column(Boolean, default=False)
    rating_instance = relationship(
        "RatingInstance", back_populates="workflow_actions"
    )  # not workflow_actions
    policy_rule = relationship("PolicyRule")
    user = relationship("User")
    # ... your existing fields ...

    def clone(
        self, db: Session, user_id=None, action_type=None, stage=None
    ) -> "WorkflowAction":
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
                    head=True,
                )
                db.add(new_workflow)

            # Commit the transaction
            db.commit()
            return new_workflow

        except Exception as e:
            db.rollback()
            raise ValueError(f"Failed to clone workflow action: {str(e)}")

    # def get_next_stage(self, db: Session) -> WorkflowStage:
    #     """Get the next stage based on current stage and policy rules"""

    #     # Get all stages configured in the policy
    #     policy_stages = (
    #         db.query(RatingAccessRule.workflow_stage)
    #         .filter(RatingAccessRule.policy_id == self.policy_rule_id)
    #         .distinct()
    #         .all()
    #     )

    #     # Convert to list of stages and sort by defined order
    #     available_stages = [stage[0] for stage in policy_stages]
    #     available_stages.sort()  # Will use the __lt__ method we defined

    #     # Add APPROVED as the final stage
    #     available_stages.append(WorkflowStage.APPROVED)

    #     # Find current stage index
    #     try:
    #         current_index = available_stages.index(self.workflow_stage)
    #         # Return next stage if exists, otherwise return current stage
    #         if current_index < len(available_stages) - 1:
    #             return available_stages[current_index + 1]
    #     except ValueError:
    #         pass

    #     return self.workflow_stage

    # # def submit(self, db: Session, user_id=None) -> 'WorkflowAction':
    #     """
    #     Submit the workflow action to the next stage.
    #     Returns the new workflow action after committing to db.
    #     """
    #     next_stage = self.get_next_stage()
    #     return self.clone(
    #         db=db,
    #         user_id=user_id,
    #         action_type=ActionRight.VIEW,
    #         stage=next_stage
    #     )

    @classmethod
    def get_active_workflow(
        cls, db: Session, rating_instance_id: UUID
    ) -> Optional["WorkflowAction"]:
        """Get the current active (head) workflow action for a rating instance"""
        return (
            db.query(cls)
            .filter(
                cls.rating_instance_id == rating_instance_id,
                cls.head == True,
                cls.is_stale == False,
            )
            .first()
        )

    def get_user_rights(self, db: Session, user_id: UUID) -> List[ActionRight]:
        """Get all allowed actions for user in current workflow stage"""
        access_rules = RatingAccessRule.get_user_access(
            db, self.policy_rule_id, user_id, self.workflow_stage
        )
        all_actions = []
        for rule in access_rules:
            all_actions.extend(rule.action_rights)
        return list(set(all_actions))  # Remove duplicates

    def can_user_perform_action(
        self, db: Session, user_id: UUID, action: ActionRight
    ) -> bool:
        """Check if user can perform specific action"""
        user_rights = self.get_user_rights(db, user_id)
        return action in user_rights

    def get_workflow_progression(self, db: Session) -> List[WorkflowStage]:
        """Get the complete workflow progression for this policy"""

        # Get all stages configured in the policy
        policy_stages = (
            db.query(RatingAccessRule.workflow_stage)
            .filter(RatingAccessRule.policy_id == self.policy_rule_id)
            .distinct()
            .all()
        )

        # Convert to list of stages and sort by defined order
        progression = [stage[0] for stage in policy_stages]
        progression.sort()  # Uses the __lt__ method from WorkflowStage

        # Add APPROVED as final stage
        progression.append(WorkflowStage.APPROVED)

        return progression

    def has_stage(self, db: Session, stage: WorkflowStage) -> bool:
        """
        Check if a specific stage exists in the workflow progression
        Note: APPROVED stage always exists as final stage
        """
        if stage == WorkflowStage.APPROVED:
            return True

        return (
            db.query(RatingAccessRule)
            .filter(
                RatingAccessRule.policy_id == self.policy_rule_id,
                RatingAccessRule.workflow_stage == stage,
            )
            .first()
            is not None
        )

    def get_previous_stage(self, db: Session) -> Optional[WorkflowStage]:
        """Get the previous stage in the workflow progression"""
        progression = self.get_workflow_progression(db)

        try:
            current_index = progression.index(self.workflow_stage)
            if current_index > 0:  # If not at first stage
                return progression[current_index - 1]
        except ValueError:
            # If current stage isn't in progression (shouldn't happen)
            pass

        return None

    # Additional helper method that might be useful
    def is_first_stage(self, db: Session) -> bool:
        """Check if current stage is the first stage in progression"""
        progression = self.get_workflow_progression(db)
        return progression[0] == self.workflow_stage if progression else False

    def is_last_stage(self, db: Session) -> bool:
        """Check if current stage is the last stage in progression"""
        progression = self.get_workflow_progression(db)
        return progression[-1] == self.workflow_stage if progression else False

    def get_stage_position(self, db: Session) -> Optional[Tuple[int, int]]:
        """
        Get the position of current stage in progression
        Returns tuple of (current_position, total_stages)
        """
        progression = self.get_workflow_progression(db)
        try:
            current_index = progression.index(self.workflow_stage)
            return (current_index + 1, len(progression))
        except ValueError:
            return None

    def submit(self, db: Session, user_id=None) -> "WorkflowAction":
        """Submit workflow action and update rating instance approval status"""
        rating_instance = (
            db.query(RatingInstance)
            .filter(RatingInstance.id == self.rating_instance_id)
            .first()
        )

        if not rating_instance:
            raise ValueError("Rating instance not found")


        if self.workflow_stage == WorkflowStage.MAKER:
            rating_instance.maker_approved = True
        elif self.workflow_stage == WorkflowStage.CHECKER:
            rating_instance.checker_approved = True
        elif self.workflow_stage == WorkflowStage.APPROVER:
            rating_instance.approver_approved = True
        db.add(rating_instance)
        db.commit()



        next_stage = self.get_next_stage(db)

        rating_instance.overall_status = next_stage
        db.add(rating_instance)
        db.commit()

        return self.clone(
            db=db, user_id=user_id, action_type=ActionRight.VIEW, stage=next_stage
        )

    def edit(self, db: Session, user_id=None) -> "WorkflowAction":
        """Edit workflow action and reset relevant approval flags"""
        if not self.head:
            raise ValueError("Cannot edit non-head workflow action")

        rating_instance = (
            db.query(RatingInstance)
            .filter(RatingInstance.id == self.rating_instance_id)
            .first()
        )
        # Reset approval flags based on editor's stage
        if self.workflow_stage in [WorkflowStage.CHECKER, WorkflowStage.APPROVER]:
            # If edited by checker or approver, reset to maker
            rating_instance.maker_approved = False
            rating_instance.checker_approved = False
            rating_instance.approver_approved = False
            next_stage = WorkflowStage.MAKER
        elif self.workflow_stage == WorkflowStage.MAKER:
            # If edited by maker, just reset maker's approval
            rating_instance.maker_approved = False
            next_stage = WorkflowStage.MAKER

        rating_instance.overall_status = next_stage
        db.add(rating_instance)

        return self.clone(
            db=db, user_id=user_id, action_type=ActionRight.EDIT, stage=next_stage
        )

    def get_next_stage(self, db: Session) -> WorkflowStage:
        """Get next stage based on current stage and approvals"""
        rating_instance = (
            db.query(RatingInstance)
            .filter(RatingInstance.id == self.rating_instance_id)
            .first()
        )

        if not rating_instance:
            raise ValueError("Rating instance not found")
        if (
            self.workflow_stage == WorkflowStage.MAKER
            and rating_instance.maker_approved
        ):
            return WorkflowStage.CHECKER
        elif (
            self.workflow_stage == WorkflowStage.CHECKER
            and rating_instance.checker_approved
        ):
            return WorkflowStage.APPROVER
        elif (
            self.workflow_stage == WorkflowStage.APPROVER
            and rating_instance.approver_approved
        ):
            return WorkflowStage.APPROVED

        return self.workflow_stage

    def can_submit(self, db: Session) -> bool:
        """Check if workflow can be submitted based on current state"""
        if not self.head or self.is_stale:
            return False

        rating_instance = (
            db.query(RatingInstance)
            .filter(RatingInstance.id == self.rating_instance_id)
            .first()
        )

        # Can't submit if already in approved state
        if self.workflow_stage == WorkflowStage.APPROVED:
            return False

        # Can't submit if current stage hasn't approved
        if (
            self.workflow_stage == WorkflowStage.MAKER
            and not rating_instance.maker_approved
            or self.workflow_stage == WorkflowStage.CHECKER
            and not rating_instance.checker_approved
            or self.workflow_stage == WorkflowStage.APPROVER
            and not rating_instance.approver_approved
        ):
            return False

        return True
