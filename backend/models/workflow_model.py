from pickle import APPEND
from re import I
from typing import Optional, Tuple

from enums_and_constants import ActionRight, WorkflowErrorCode, WorkflowStage
from models.base import Base


from sqlalchemy import (
    UUID,
    Boolean,
    Column,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Integer,
    String,
    null,
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

    user_id = Column(UUID, ForeignKey("user.id"),nullable=True)
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
        self, db: Session, user_id, action_type=None, stage=None,rating_instance_id=None,
    ) -> "WorkflowAction":
        """
        Clone the current workflow action and handle all database operations.
        Returns the new workflow action instance after committing to db.
        """
        if not self.head:
            raise ValueError("Unable to clone the workflow as it is not the head")
        change_head=True
        # change_head= False if action_type and action_type==ActionRight.APPROVE else True
        try:
            # Start a nested transaction
            with db.begin_nested():
                # Update current workflow action
                if change_head:
                    self.head = False
                    self.is_stale = True
                db.add(self)
                if action_type in [ActionRight.MOVE_TO_NEXT_STAGE,ActionRight.EXIT,ActionRight.INIT]:
                    """
                    its s system trigger, not really a user action, when a set of conditions are met the system automatically moves the workflow to the next stage, and ehnce we dont want it to eb associated with any one user
                    this is particularly needed hwne say 3 approvals are needed for the wf to mvoe to next stage, in this case it is the systme that checks if 3 approvals are in palce and then transfers it. itwould be incorrect to record the last approvers user id as hte uset that moved the wf to the next stage
                    """
                    action_done_by=None 
                else:
                    action_done_by=user_id
                # Create new workflow action
                new_workflow = WorkflowAction(
                    id=uuid4(),
                    workflow_cycle_id=self.workflow_cycle_id,
                    customer_id=self.customer_id,
                    action_count_customer_level=self.action_count_customer_level + 1,
                    user_id=action_done_by,
                    action_type=action_type if action_type else self.action_type,
                    rating_instance_id= rating_instance_id if rating_instance_id else self.rating_instance_id,
                    workflow_stage=stage if stage else self.workflow_stage,
                    description=None,
                    preceding_action_id=self.id,
                    succeeding_action_id=None,
                    is_stale=False if change_head  else True,
                    policy_rule_id=self.policy_rule_id,
                    head=True if change_head else False,
                )
                db.add(new_workflow)

            # Commit the transaction
            db.commit()
            return new_workflow

        except Exception as e:
            db.rollback()
            raise ValueError(f"Failed to clone workflow action: {str(e)}")


    @classmethod
    def get_active_workflow(
        cls, db: Session, work_flow_cycle_id: UUID
    ) -> Optional["WorkflowAction"]:
        """Get the current active (head) workflow action for a rating instance"""
        return (
            db.query(cls)
            .filter(
                cls.workflow_cycle_id== work_flow_cycle_id,
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



    def is_latest_action(self,db:Session)->bool:
        return self.head 
    
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

    def record_action(self,action: ActionRight,user_id,db:Session)->'WorkflowAction':

        action_work_step= self.clone( db=db, action_type=action, stage=self.workflow_stage,user_id=user_id )
        return action_work_step

    def approve(self, db: Session, user_id=None) -> Optional["WorkflowAction"]:
        from check_policy_rule import get_approval_tracking
        """Approve workflow action and update rating instance approval status"""
        rating_instance = (
            db.query(RatingInstance)
            .filter(RatingInstance.id == self.rating_instance_id)
            .first()
        )

        if not rating_instance:
            raise ValueError("Rating instance not found")
        was_previous_action_an_edit = True if self.action_type ==ActionRight.EDIT else False
        approval_wf_action = self.record_action( db=db, action=ActionRight.APPROVE,user_id=user_id )
        is_this_stage_all_approved = approval_wf_action.check_approval_completion(db)
        # self.action_type=ActionRight.APPROVE
        # self.make_head(db=db) # we make the currnet workflow the head, it just makes it easier to clone. Essentially in the workflow, we dont allow the Approval step to be a head
        if not is_this_stage_all_approved:
            #means approval not done, we need more Approvals in the same stage. So we make the step previous to the 
            #but before that we need to check if there was an edit in this stage that hasnt been approved by the maker yet, in which case, it needs to go back to the maker stage for their approval
            if was_previous_action_an_edit:
                self.exit_stage(db)
                new_maker_stage_initiated= self.initiate_next_stage(next_stage=WorkflowStage.MAKER,db=db)
                # cloned_as_maker_wf=exited_step.clone( db=db, action_type=ActionRight.MOVE_TO_NEXT_STAGE, stage=next_stage,user_id=None )
                return new_maker_stage_initiated if new_maker_stage_initiated else None
            else:
                return approval_wf_action
                # cloned_wf=self.clone(db,user_id=self.user_id,action_type=ActionRight,stage=self.workflow_stage)
        else:
            # All approvals needed for this stage is done. Move to next stage
            exited_step= self.exit_stage(db)

            next_stage =   WorkflowStage.MAKER if was_previous_action_an_edit else self.get_next_stage(db)
            next_stage_initiated= self.initiate_next_stage(next_stage=next_stage,db=db)

            # db.add(rating_instance)
            return next_stage_initiated 
        
    def exit_stage(self,db:Session) -> Optional['WorkflowAction']:
        latest_step=WorkflowAction.get_active_workflow(db=db,work_flow_cycle_id=self.workflow_cycle_id)
        if latest_step:
            exited_step= latest_step.clone(db=db,action_type=ActionRight.EXIT,stage=self.workflow_stage,user_id=None)
            return exited_step
        return None
    
    def initiate_next_stage(self,next_stage:WorkflowStage,db:Session)-> Optional['WorkflowAction']:
        latest_step=WorkflowAction.get_active_workflow(db=db,work_flow_cycle_id=self.workflow_cycle_id)
        if latest_step:
            initiated_step= latest_step.clone(db=db,action_type=ActionRight.INIT,stage=next_stage,user_id=None)
            return initiated_step
        else:
            return None

    # def make_head(self, db: Session):
    #     # Update all workflow actions in the same cycle to head=False
    #     db.query(WorkflowAction)\
    #         .filter(WorkflowAction.workflow_cycle_id == self.workflow_cycle_id)\
    #         .filter(WorkflowAction.id != self.id)\
    #         .filter(WorkflowAction.is_stale ==False)\
    #         .update({"head": False,"is_stale": True})
    
    #     # Set current workflow action as head
    #     self.head = True
    #     self.is_stale = False
    #     db.add(self)
    #     db.commit()

    def check_approval_completion(self,db:Session):
    
        from check_policy_rule import get_approval_tracking
        # approval_tracking = get_approval_tracking( rating_instance_id=self.rating_instance_id, workflow_action_id=self.id, db=db)
        approval_tracking = get_approval_tracking( rating_instance_id=self.rating_instance_id, db=db)
        return approval_tracking.get_stage_level_approval_status(self.workflow_stage)



    def edit(self, db: Session, user_id=None) -> "WorkflowAction":
        """Edit workflow action and reset relevant approval flags"""
        if not self.head:
            raise ValueError("Cannot edit non-head workflow action")

        if self.action_type == ActionRight.EDIT:
            #if already in edit, no need to create another clone
            return self
        rating_instance = (
            db.query(RatingInstance)
            .filter(RatingInstance.id == self.rating_instance_id)
            .first()
        )
        if rating_instance:
            if self.action_type!=ActionRight.EDIT and self.action_type !=ActionRight.APPROVE:
                cloned_rating_instance= rating_instance.clone_rating_instance(db=db)
                cloned_wf= self.clone(db=db,user_id=user_id,rating_instance_id=cloned_rating_instance.id,action_type=ActionRight.EDIT)
                return cloned_wf
        else:
            return self

    # def get_next_stage(self, db: Session) -> WorkflowStage:
    #     """Get next stage based on current stage and approvals"""
    #     rating_instance = (
    #         db.query(RatingInstance)
    #         .filter(RatingInstance.id == self.rating_instance_id)
    #         .first()
    #     )
    #     approval_tracking= get_approval_tracking(rating_instance_id=self.rating_instance_id,db=db)
    #     if not rating_instance:
    #         raise ValueError("Rating instance not found")
    #     if (
    #         self.workflow_stage == WorkflowStage.MAKER
    #         # and rating_instance.maker_approved
    #     ):
    #         next_stage= WorkflowStage.CHECKER
    #         if approval_tracking.get_stage_level_approval_status(next_stage):
    #             next_stage=WorkflowStage.APPROVER
    #             #i want to recursively check this
    #         return WorkflowStage.CHECKER
    #     elif (
    #         self.workflow_stage == WorkflowStage.CHECKER
    #         # and rating_instance.checker_approved
    #     ):
    #         return WorkflowStage.APPROVER
    #     elif (
    #         self.workflow_stage == WorkflowStage.APPROVER
    #         # and rating_instance.approver_approved
    #     ):
    #         return WorkflowStage.APPROVED

    #     return self.workflow_stage


    def get_next_stage(self, db: Session) -> WorkflowStage:
        """Get next stage based on current stage and approvals, recursively checking if next stage is already approved"""

        from check_policy_rule import get_approval_tracking
        def check_next_stage(current_stage: WorkflowStage, approval_tracking) -> WorkflowStage:
            if current_stage == WorkflowStage.APPROVED:
                return WorkflowStage.APPROVED
                
            stage_progression = {
                WorkflowStage.MAKER: WorkflowStage.CHECKER,
                WorkflowStage.CHECKER: WorkflowStage.APPROVER,
                WorkflowStage.APPROVER: WorkflowStage.APPROVED
            }
            
            next_stage = stage_progression.get(current_stage)
            if not next_stage:
                return current_stage
                
            # If next stage is already approved, recursively check the stage after that
            if approval_tracking.get_stage_level_approval_status(next_stage):
                return check_next_stage(next_stage, approval_tracking)
                
            return next_stage

        rating_instance = (
            db.query(RatingInstance)
            .filter(RatingInstance.id == self.rating_instance_id)
            .first()
        )
        
        if not rating_instance:
            raise ValueError("Rating instance not found")
            
        approval_tracking = get_approval_tracking(
            rating_instance_id=self.rating_instance_id,
            db=db
        )
        
        return check_next_stage(self.workflow_stage, approval_tracking)

    def get_previous_stage(self, db: Session) -> WorkflowStage:
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
            # and rating_instance.maker_approved
        ):
            return None
        elif (
            self.workflow_stage == WorkflowStage.CHECKER
            # and rating_instance.checker_approved
        ):
            return WorkflowStage.MAKER
        elif (
            self.workflow_stage == WorkflowStage.APPROVER
            # and rating_instance.approver_approved
        ):
            return WorkflowStage.CHECKER

        return self.workflow_stage

    def can_submit(self, db: Session) -> bool:

        from check_policy_rule import get_approval_tracking
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
        # approval_tracking= get_approval_tracking(rating_instance_id=rating_instance.id,workflow_action_id=self.id,db=db)
        approval_tracking= get_approval_tracking(rating_instance_id=rating_instance.id,db=db)
        if approval_tracking:
            if approval_tracking.get_stage_level_approval_status(self.workflow_stage):
                return False
        return True



    def can_edit(self, db: Session) -> Tuple[bool, Optional[WorkflowErrorCode]]:
        """Check if workflow can be edited based on current state"""
        if not self.head:
            return False, WorkflowErrorCode.NOT_HEAD_ACTION
            
        if self.is_stale:
            return False, WorkflowErrorCode.STALE_WORKFLOW

        rating_instance = (
            db.query(RatingInstance)
            .filter(RatingInstance.id == self.rating_instance_id)
            .first()
        )

        if self.workflow_stage == WorkflowStage.APPROVED:
            return False, WorkflowErrorCode.EDIT_IN_APPROVED

        if self.action_type == ActionRight.EDIT:
            return False, WorkflowErrorCode.ALREADY_IN_EDIT

        return True, None
