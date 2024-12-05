
from uuid import UUID
from models.models import Role, User

import sys

from models.policy_rules_model import PolicyRule, RatingStageApprovalRule
from models.rating_instance_model import RatingInstance
sys.path.append("/home/ashleyubuntu/ratingModelPython/backend")
from main import init_db
from rating_model_instance import generate_qualitative_factor_data
from security import AuthHandler, RequiresLoginException
from enums_and_constants import AcceptFlow, ActionRight, EditFlow, RejectionFlow, WorkflowStage
from config import create_engine_and_session,DB_NAME

from sqlalchemy.orm import Session
from schema.approval_tracking import ApprovalTracking


# from main import init_db
# init_db(DB_NAME)
# init_db(DB_NAME)
# _, db = create_engine_and_session(DB_NAME)
# user=db.query(User).filter(User.email=='ashley.cherian@gmail.com').first()

# policy=db.query(PolicyRule).filter(PolicyRule.name=='Large Corporate Credit Approval Policy').first()

# approvers=policy.get_approvers_for_policy(WorkflowStage.MAKER)


def get_approval_tracking(rating_instance_id: str |UUID, db: Session) -> ApprovalTracking:
    from models.workflow_model import WorkflowAction

    # Get the rating instance and its associated policy
    rating_instance = db.query(RatingInstance).filter(RatingInstance.id == rating_instance_id).first()
    policy = (db.query(PolicyRule)
             .filter(PolicyRule.business_unit_id == rating_instance.customer.business_unit_id)
             .filter(PolicyRule.is_active == True)
             .first())

    # Get approval rules for each stage
    approval_rules = (db.query(RatingStageApprovalRule)
                     .filter(RatingStageApprovalRule.policy_id == policy.id)
                     .all())

    # Get all workflow actions for this rating instance to track actual approvers
    workflow_actions = (db.query(WorkflowAction)
                       .filter(WorkflowAction.rating_instance_id == rating_instance_id)
                       .all())

    # Group rules by stage
    maker_rules = []
    checker_rules = []
    approver_rules = []
    
    for rule in approval_rules:
        if rule.workflow_stage == WorkflowStage.MAKER:
            maker_rules.append(rule)
        elif rule.workflow_stage == WorkflowStage.CHECKER:
            checker_rules.append(rule)
        elif rule.workflow_stage == WorkflowStage.APPROVER:
            approver_rules.append(rule)

    # Get all approver role IDs
    maker_role_ids = [rule.approver_role_id for rule in maker_rules]
    checker_role_ids = [rule.approver_role_id for rule in checker_rules]
    approver_role_ids = [rule.approver_role_id for rule in approver_rules]

    # Get all roles in one query
    all_role_ids = maker_role_ids + checker_role_ids + approver_role_ids
    roles = db.query(Role).filter(Role.id.in_(all_role_ids)).all()
    roles_by_id = {role.id: role for role in roles}

    # Get actual approvers from workflow actions for each stage
    maker_approvers = [
        action.user for action in workflow_actions 
        if action.workflow_stage == WorkflowStage.MAKER and action.action_type==ActionRight.APPROVE 
    ]

    checker_approvers = [
        action.user for action in workflow_actions 
        if action.workflow_stage == WorkflowStage.CHECKER and action.action_type==ActionRight.APPROVE
    ]

    approver_approvers = [
        action.user for action in workflow_actions 
        if action.workflow_stage == WorkflowStage.APPROVER and action.action_type==ActionRight.APPROVE 
    ]

    approval_tracking= ApprovalTracking(
        required_maker_approvers=maker_rules[0].no_of_approvals_needed_for_stage if maker_rules else 0,
        required_checker_approvers=checker_rules[0].no_of_approvals_needed_for_stage if checker_rules else 0,
        required_approver_approvers=approver_rules[0].no_of_approvals_needed_for_stage if approver_rules else 0,
        
        allowed_maker_approvers=[roles_by_id[role_id] for role_id in maker_role_ids],
        allowed_checker_approvers=[roles_by_id[role_id] for role_id in checker_role_ids],
        allowed_approver_approvers=[roles_by_id[role_id] for role_id in approver_role_ids],
        
        acutal_maker_approvers=maker_approvers,
        actual_checker_approvers=checker_approvers,
        actual_approver_approvers=approver_approvers
    )
    approval_tracking.update_approval_status()
    return approval_tracking