# import uuid

# from click import edit
# from enums_and_constants import EditFlow, WorkflowStage,RejectionFlow
# from logging import raiseExceptions
# from typing import List, Tuple
# from uuid import UUID, uuid4

# from calculate_derived_scores import calculate_derived_scores
# from dependencies import auth_handler, ensure_uuid
# from enums_and_constants import ActionRight, WorkflowErrorCode
# from models.models import Customer, Role, User
# from models.rating_instance_model import RatingFactorScore, RatingInstance
# from models.rating_model_model import RatingModel, ScoreToGradeMapping
# from models.statement_models import FinancialStatement, Template
# from models.workflow_model import WorkflowAction
# from rating_model import configure_rating_model_factors, get_or_create_rating_model
# # from rating_model_instance import (
# #     check_all_user_inputs_factor_availability,
# #     get_quant_factor_inputs,
# #     score_quantitative_factors,
# #     update_qualitative_factor_scores,
# # )
# from rating_model_instance import (
#     check_all_user_inputs_factor_availability,
# )
# from rating_model_instance import (
#     score_quantitative_factors,
# )
# from rating_model_instance import (
#     update_qualitative_factor_scores,
# )
# from rating_model_instance import (
#     get_quant_factor_inputs,
# )
# from rating_workflow_processing_1 import get_applicable_rating_model_for_business_unit, get_policy_rules_for_customer
# from schema.schema import RatingFactorScore as RatingFactorScoreSchema, RatingModelApplicabilityRulesCreate
# from schema.schema import (
#     RatingFactorScoreCreate,
#     RatingInstanceCreate,
#     WorkflowActionCreate,
# )
# from schema.schema import User as UserSchema
# from schema.schema import WorkflowAction as WorkflowActionSchema
# from sqlalchemy import and_
# from sqlalchemy.orm import Session

# from schema.schema import WorkflowError
# from schema.schema import ErrorResponse
# from security import get_hashed_password
# from schema import schema

# def create_workflow_action(db: Session, customer_id: UUID, action_type: ActionRight, user: UserSchema) -> WorkflowAction:
#     if user.id is None:
#         raise ValueError("User ID cannot be None when creating workflow action")
#     latest_step_db = db.query(WorkflowAction).filter(
#         WorkflowAction.customer_id == customer_id
#     ).order_by(WorkflowAction.action_count_customer_level.desc()).first()
#     latest_step=schema.WorkflowAction(**latest_step_db.__dict__)
#     # Validate using Pydantic schema
#     workflow_data = WorkflowActionCreate(
#         id=uuid4(),
#         workflow_cycle_id=uuid4(),
#         customer_id=customer_id,
#         workflow_stage=WorkflowStage.MAKER,
#         action_type=action_type,
#         description=f"{action_type.value} step",
#         action_count_customer_level=(
#             latest_step.action_count_customer_level + 1) if latest_step else 1,
#         user_id=user.id,
#         head=True,
#         is_stale=False
#     )
#     new_step = WorkflowAction(**workflow_data.model_dump())
#     db.add(new_step)
#     db.flush()
#     return new_step


# def clone_rating_instance(db: Session, original_instance: RatingInstanceCreate, new_workflow_step: WorkflowActionSchema) -> schema.RatingInstance:
#     # Validate using Pydantic schema
#     if new_workflow_step.id is None:
#         raise ValueError("new_workflow_step ID cannot be None when performing action")
    
    
#     instance_data = RatingInstanceCreate(
#         id=uuid4(),
#         customer_id=original_instance.customer_id,
#         financial_statement_id=original_instance.financial_statement_id,
#         rating_model_id=original_instance.rating_model_id,
#         workflow_action_id=new_workflow_step.id,
#         overall_status=new_workflow_step.workflow_stage,
#         incomplete_financial_information=original_instance.incomplete_financial_information,
#         missing_financial_fields=original_instance.missing_financial_fields,
#         overall_score=original_instance.overall_score,
#         overall_rating=original_instance.overall_rating
#     )

#     new_instance_db = RatingInstance(**instance_data.model_dump())
#     db.add(new_instance_db)
#     db.flush()
#     new_instance=schema.RatingInstance(**new_instance_db.__dict__)
#     if new_instance.id is None:
#         raise ValueError("new_instance ID cannot be None when performing action")

#     rf_scores_db= db.query(RatingFactorScore).filter(RatingFactorScore.rating_instance_id == original_instance.id).all()

#     rf_scores= [schema.RatingFactorScore(**rf.__dict__) for rf in rf_scores_db]
        
#     # Clone and validate factor scores
#     for score in rf_scores:
#         score_data = RatingFactorScoreCreate(
#             rating_instance_id=new_instance.id,
#             rating_factor_id=score.rating_factor_id,
#                 raw_value_text=score.raw_value_text,
#                 raw_value_float= score.raw_value_float,
#                 score= score.score
            
#         )
#         new_score = RatingFactorScore(**score_data.model_dump())
#         db.add(new_score)
#         db.commit()
#     return new_instance


# def process_rating_instance(db: Session, rating_instance: RatingInstance, user: UserSchema):
#     """Process a rating instance and create a new workflow step"""
#     try:
#         # rating_instance.overall_status = ActionRight.SUBMITTED
        
#         # Process the rating
#         quant_factor_scores, incomplete_financial_information, missing_fields = get_quant_factor_inputs(
#             db, rating_instance)

#         if incomplete_financial_information:
#             rating_instance.incomplete_financial_information = True
#             rating_instance.missing_financial_fields = missing_fields
#             db.commit()
#             return rating_instance

#         if check_all_user_inputs_factor_availability(db, rating_instance):
#             score_quantitative_factors(db, rating_instance)
#             update_qualitative_factor_scores(db, rating_instance)
#             calculate_derived_scores(db, rating_instance)
            
#             db.commit()
#             return rating_instance
        
#         return rating_instance

#     except Exception as e:
#         print(f"Error processing rating instance: {str(e)}")
#         db.rollback()
#         raise

# def get_current_workflow_status(rating_instance: RatingInstance) -> ActionRight:
#     """Get the current workflow status from the most recent action"""
#     current_action = rating_instance.current_workflow_action
#     return current_action.action_type if current_action else ActionRight.VIEW

# def get_workflow_history(db: Session, rating_instance_id: UUID) -> List[WorkflowAction]:
#     """Get all workflow actions for a rating instance in chronological order"""
#     return db.query(WorkflowAction)\
#         .filter(WorkflowAction.rating_instance_id == rating_instance_id)\
#         .order_by(WorkflowAction.action_count_customer_level)\
#         .all()

# def review_rating_instance(db: Session, rating_instance: RatingInstance, workflow_id:UUID, reviewer: User, approved: bool, comments: str):
#     """Review a rating instance and create appropriate workflow actions"""
#     try:
#         # Create a new workflow action for the review
#         review_status = ActionRight.VIEW
        
#         # workflow_step = WorkflowAction(
#         #     id=uuid4(),
#         #     customer_id=rating_instance.customer_id,
#         #     action_type=review_status,
#         #     action_by=reviewer.id,
#         #     rating_instance_id=rating_instance.id,
#         #     action_count_customer_level=len(rating_instance.workflow_actions) + 1,
#         #     description=comments,
#         #     preceding_action_id=rating_instance.current_workflow_action.id if rating_instance.current_workflow_action else None
#         # )
#         workflow= db.query(WorkflowAction).filter(WorkflowAction.id==workflow_id)
#         #clone rating instance here
#         # db.add(workflow_step)
#         rating_instance.overall_status = review_status
        
#         db.commit()
#         return rating_instance

#     except Exception as e:
#         print(f"Error reviewing rating instance: {str(e)}")
#         db.rollback()
#         raise


# def check_right(stage_rule: WorkflowStageConfig, right_to_check: ActionRight) -> bool:
#     """
#     Check if a given right exists in stage_rule.rights using type-safe comparison
#     """
#     return any(ActionRight.from_string(right) == right_to_check for right in stage_rule.rights)

# def check_ability_to_submit(workflow_action:WorkflowAction,rating_instance:RatingInstance):

#         if (workflow_action.action_type!=ActionRight.SUBMIT):
#             if (workflow_action.head):
#                 return True
#             else:
#                 raise ValueError(f"Not the head anymore")
#         else:
#             raise ValueError(f"Already submitted")

            
# def check_if_existing_workflow_for_customer(customer_id:UUID| str)    :
#         existing_workflow= db.query(WorkflowAction).filter(WorkflowAction.customer_id==customer_id).first()
#         if existing_workflow and existing_workflow.id:
#             return True
#         else:
#             return False

# def get_workflow_stage_roles(policy_rule_id:UUID,wf_stage_to_check:WorkflowStage,db:Session) :
     
#     stage = db.query(WorkflowStageConfig).filter(
#             WorkflowStageConfig.policy_id == policy_rule_id,
#             WorkflowStageConfig.stage == wf_stage_to_check
#         ).first()
#     if stage:
#         allowed_role_ids= stage.allowed_roles

#         roles = db.query(Role).filter(
#             Role.id.in_(allowed_role_ids)
#         ).all()
#         return stage,roles
#     if not stage:
#             if wf_stage_to_check==WorkflowStage.MAKER:
#                 raise WorkflowError(code=WorkflowErrorCode.MISSING_MAKER_STAGE)
#             else:
#                  raise ValueError(f"Stage not found : {wf_stage_to_check.value}")


# def create_rating_workflow_for_customer(db:Session, customer: Customer, user: User):
#     try:
#         # Check policy rule
#         policy_rule = get_policy_rules_for_customer(cif_number=None,customer_id=customer.id)
#         if not policy_rule:
#             raise WorkflowError(
#                 code=WorkflowErrorCode.POLICY_RULE_NOT_FOUND,
#                 details={"cif_number": cif_number}
#             )

#         # Get maker stage configuration
#         maker_stage, roles =get_workflow_stage_roles(policy_rule.id,WorkflowStage.MAKER,db)
#         # Check user roles
#         allowed_role_names = [role.name for role in roles]
#         allowed_role_ids = [str(role.id) for role in roles]
#         has_maker_role = any(role in allowed_role_ids for role in user.role)
#         if not has_maker_role:
#             raise WorkflowError(
#                 code=WorkflowErrorCode.UNAUTHORIZED_ROLE,
#                 details={"user_roles": user.role, "required_roles": allowed_role_names}
#             )

#         # Check existing workflow
#         if check_if_existing_workflow_for_customer(customer_id=customer.id):
#             raise WorkflowError(code=WorkflowErrorCode.WORKFLOW_EXISTS)

#         # Check creation rights
#         if not check_right(maker_stage, ActionRight.CREATE):
#             raise WorkflowError(
#                 code=WorkflowErrorCode.UNAUTHORIZED_ACTION,
#                 details={"action": "CREATE"}
#             )

#         # Create workflow
#         work_flow_cycle_id = uuid4()
#         initial_workflow_data = WorkflowActionSchema(
#             id=uuid4(),
#             workflow_cycle_id=work_flow_cycle_id,
#             customer_id=customer.id,
#             workflow_stage=WorkflowStage.MAKER,
#             action_type=ActionRight.CREATE,
#             action_count_customer_level=1,
#             head=True,
#             is_stale=False,
#             policy_rule_id=policy_rule.id,
#             user_id=str(user.id),
#             preceding_action_id=None,
#             succeeding_action_id=None
#         )
        
#         initial_step = WorkflowAction(**initial_workflow_data.model_dump(exclude_none=True))
#         db.add(initial_step)
        
#         # Get financial statement
#         statement = db.query(FinancialStatement).filter(
#             FinancialStatement.customer_id == customer.id,
#             FinancialStatement.financials_period_year == 2023
#         ).first()
        
#         if not statement:
#             raise WorkflowError(
#                 code=WorkflowErrorCode.STATEMENT_NOT_FOUND,
#                 details={"customer_id": str(customer.id), "year": 2023}
#             )

#         db.commit()

#         return initial_step

#     except WorkflowError as e:
#         db.rollback()
#         raise e
#     except Exception as e:
#         db.rollback()
#         raise WorkflowError(
#             code=WorkflowErrorCode.UNAUTHORIZED_ACTION,
#             message=f"Unexpected error: {str(e)}"
#         )

# def create_rating_instance_for_initial_step(wf_data:WorkflowAction,rating_model_id:UUID, statement_id:UUID,user:User, db:Session):
#             customer_id=wf_data.customer_id
#                 # Create initial rating instance with validation
#             instance_data = RatingInstanceCreate(
#                 id=uuid4(),
#                 customer_id=ensure_uuid(customer_id),
#                 financial_statement_id=ensure_uuid(statement_id),
#                 rating_model_id=rating_model.id,
#                 workflow_action_id=wf_data.id,
#                 overall_status=WorkflowStage.MAKER
#             )
#             initial_rating_instance = RatingInstance(**instance_data.model_dump())
#             db.add(initial_rating_instance)
#             db.add(wf_data)
#             wf_data.rating_instance_id = initial_rating_instance.id
#             db.commit()
#             generate_qualitative_factor_data(db,initial_rating_instance)
#             # Process the rating instance
#             processed_instance = process_rating_instance(
#                 db, initial_rating_instance, user)
#             return processed_instance

# def get_customer_by_id(db:Session,customer_id:UUID):
#     customer=db.query(Customer).filter(Customer.id==customer_id).first()
#     return customer

# def submit_rating_instance(wf_data:WorkflowAction,user:User,db:Session):
#     stage=get_workflow_stage_roles(policy_rule_id=wf_data.policy_rule_id,wf_stage_to_check=wf_data.workflow_stage,db=db) 
#     if check_right(stage,ActionRight.SUBMIT):
#             wf_data.action_type=ActionRight.SUBMIT
#             db.add(wf_data)
#             db.commit()
#     else:
#             raise ValueError(f"User {user.name} does not have required SUBMIT Righjts for this policy")
#     return wf_data

# from typing import Set
# from enum import Enum
# from sqlalchemy.orm import Session

# def identify_available_actions_for_wf_step(workflow_action: WorkflowAction, db: Session) -> Set[ActionRight]:
#     """
#     Identifies which actions are available for the current workflow step.
    
#     Args:
#         workflow_action: Current workflow action
#         db: Database session
        
#     Returns:
#         Set of ActionRight enums representing available actions
#     """
#     # Get stage configuration
#     stage = db.query(WorkflowStageConfig).filter(
#         WorkflowStageConfig.policy_id == workflow_action.policy_rule_id,
#         WorkflowStageConfig.stage == workflow_action.workflow_stage
#     ).first()
    
#     if not stage:
#         return set()  # No actions available if stage config not found
        
#     available_actions: Set[ActionRight] = set()
    
#     # Helper function to check if workflow was ever submitted
#     def was_ever_submitted() -> bool:
#         return db.query(WorkflowAction).filter(
#             WorkflowAction.workflow_cycle_id == workflow_action.workflow_cycle_id,
#             WorkflowAction.action_type == ActionRight.SUBMIT
#         ).first() is not None
    
#     # Helper function to check if rating instance exists
#     def has_rating_instance() -> bool:
#         return workflow_action.rating_instance_id is not None
    
#     # Helper function to check if rating has overall score
#     def has_overall_score() -> bool:
#         if not workflow_action.rating_instance_id:
#             return False
#         rating = db.query(RatingInstance).filter(
#             RatingInstance.id == workflow_action.rating_instance_id
#         ).first()
#         return rating is not None and rating.overall_score is not None

#     # Process each potential action based on stage rights and conditions
#     for right in stage.rights:
#         action_right = ActionRight.from_string(right)
        
#         if action_right == ActionRight.CREATE:
#             # CREATE allowed only once if no rating instance exists
#             if not has_rating_instance():
#                 available_actions.add(action_right)
                
#         elif action_right == ActionRight.EDIT:
#             # EDIT allowed if not submitted
#             if not was_ever_submitted():
#                 available_actions.add(action_right)
                
#         elif action_right == ActionRight.DELETE:
#             # DELETE allowed if not submitted
#             if not was_ever_submitted():
#                 available_actions.add(action_right)
                
#         elif action_right == ActionRight.VIEW:
#             # VIEW always allowed if in rights
#             available_actions.add(action_right)
                
#         elif action_right == ActionRight.COMMENT:
#             # COMMENT allowed if not submitted
#             if not was_ever_submitted():
#                 available_actions.add(action_right)
                
#         elif action_right == ActionRight.TRANSFER:
#             # TRANSFER always allowed if in rights
#             available_actions.add(action_right)
                
#         elif action_right == ActionRight.SUBMIT:
#             # SUBMIT allowed if has rating with overall score and not previously submitted
#             if has_rating_instance() and has_overall_score() and not was_ever_submitted():
#                 available_actions.add(action_right)
    
#     return available_actions

# def check_if_user_has_any_associated_roles(user:User,workflow_action:WorkflowAction,db:Session):
#     # stage = db.query(WorkflowStageConfig).filter(
#     #     WorkflowStageConfig.policy_id == workflow_action.policy_rule_id,
#     #     WorkflowStageConfig.stage == workflow_action.workflow_stage
#     # ).first()
#     # roles_allowed = stage.allowed_roles


#     stage, roles =get_workflow_stage_roles(workflow_action.policy_rule_id,workflow_action.workflow_stage,db=db)
#         # Check user roles
#     allowed_role_names = [role.name for role in roles]
#     allowed_role_ids = [str(role.id) for role in roles]
#     has_role = any(role in allowed_role_ids for role in user.role)
#     if not has_role:
#             raise WorkflowError(
#                 code=WorkflowErrorCode.UNAUTHORIZED_ROLE,
#                 details={"user_roles": user.role, "required_roles": allowed_role_names}
#             )

#     else:
#         return True

# if __name__ == "__main__":
#     from customer_financial_statement import FsApp
#     from main import DB_NAME, create_engine_and_session, init_db
#     from rating_model_instance import generate_qualitative_factor_data
#     from security import AuthHandler, RequiresLoginException
#     from sqlalchemy import create_engine
#     from sqlalchemy.orm import sessionmaker,joinedload
#     from schema.schema import RatingModelApplicabilityRulesCreate
#     from schema.schema import RatingModelApplicabilityRules as RatingModelApplicabilityRulesSchema
#     from models import rating_model_model
#     init_db(DB_NAME)
#     _, db = create_engine_and_session(DB_NAME)
#     configure_rating_model_factors(db)
#     app = FsApp(db)
#     cif_number="CIF-123456"
#     customer = app.create_statement_data_for_customer(cif_number)
#     print(f"Created statement data for customer: {customer.customer_name}")

#     template = db.query(Template).filter(
#         Template.name == "FinTemplate").first()
#     rating_model = get_or_create_rating_model(
#         session=db, template=template, model_name='Corporate')
#     customer = db.query(Customer).options(joinedload(Customer.business_unit)).filter(Customer.cif_number=='CIF-123456').first()
#     if rating_model:
#         ratingModelApplicable=RatingModelApplicabilityRulesCreate(rating_model=rating_model,rating_model_id=rating_model.id,business_unit=customer.business_unit,business_unit_id=customer.business_unit.id)

#         # db.add(rating_model_model.RatingModelApplicabilityRules(**ratingModelApplicable.__dict__))
#     # Use exclude to remove the relationship fields
#         db.add(rating_model_model.RatingModelApplicabilityRules(**ratingModelApplicable.model_dump(exclude={'rating_model', 'business_unit'})))
#         db.commit()
#     # create_default_policy(db,default_policy, customer.business_unit)
#     # Create score to grade mappings
#     mapping_data: List[Tuple[float, float, int]] = [
#         (float('-inf'), 0.50, 12),
#         (0.50, 1.10, 11),
#         (1.10, 1.60, 11),
#         (1.60, 2.10, 11),
#         (2.10, 2.60, 10),
#         (2.60, 3.10, 10),
#         (3.10, 3.60, 10),
#         (3.60, 4.00, 9),
#         (4.00, 4.50, 9),
#         (4.50, 5.00, 9),
#         (5.00, 5.50, 8),
#         (5.50, 6.00, 8),
#         (6.00, 6.40, 7),
#         (6.40, 6.80, 7),
#         (6.80, 7.20, 6),
#         (7.20, 7.60, 5),
#         (7.60, 8.00, 4),
#         (8.00, 8.40, 3),
#         (8.40, 8.80, 2),
#         (8.80, 10.00, 1)
#     ]

#     mappings = [
#         ScoreToGradeMapping(
#             rating_model_id=rating_model.id,
#             bin_start=start,
#             bin_end=end,
#             grade=str(grade)
#         )
#         for start, end, grade in mapping_data
#     ]

#     db.add_all(mappings)
#     db.commit()
    
#     auth_handler=AuthHandler()

#     user=db.query(User).filter(User.email=='ashley.cherian@gmail.com').first()

#     customer=db.query(Customer).filter(Customer.cif_number==cif_number).first()
#     #identify the rating model to be used for a business unit
#     initial_step=create_rating_workflow_for_customer(db,customer=customer,user=user)
#     rating_model_id= get_applicable_rating_model_for_business_unit(db,customer.business_unit_id)
#             # Get a financial statement
#     statement = db.query(FinancialStatement).filter(
#                 FinancialStatement.customer_id == customer.id).filter(FinancialStatement.financials_period_year==2023).first()
#     rating_instance = create_rating_instance_for_initial_step(initial_step,rating_model_id,statement.id,user,db) 
#     if check_if_user_has_any_associated_roles(user,workflow_action=initial_step,db=db):
#         print("Has rights to perform available actions; else only view would have been allowed")
#         available_actions= identify_available_actions_for_wf_step(initial_step,db)
#     else:
#         available_actions=None

#     policy_rule= get_policy_rules_for_customer(cif_number=cif_number,customer_id=None) 
#     if  not policy_rule:
#         raise ValueError(f"Policy rule not found for customer {cif_number}")
#     # check if the user has rights to create a new workflow
#     roles=user.role

#     #Maker roles for this policy
#     if policy_rule:
#         # Get Maker roles for this policy
#         maker_stage = db.query(WorkflowStageConfig).filter( WorkflowStageConfig.policy_id == policy_rule.id, WorkflowStageConfig.stage == WorkflowStage.MAKER ).first()
    
#     allowed_roles = maker_stage.allowed_roles  # Assuming this is a list of role IDs

#     has_maker_role = any(role in allowed_roles for role in roles)
#     if not has_maker_role:
#         raise ValueError("User does not have required maker role for this policy")



#     # # iniitate new rating workflow process
#     # if check_if_existing_workflow_for_customer(customer_id=customer.id):
#     #     raise ValueError(f" Workflow already exists")
#     # else:
#     #     work_flow_cycle_id=uuid4()
#     #     if check_right(maker_stage,ActionRight.CREATE):
#     #         # Create initial workflow step with validation
#     #         initial_workflow_data = WorkflowActionSchema(
#     #             id=uuid4(),
#     #             workflow_cycle_id=work_flow_cycle_id,
#     #             customer_id=customer.id,
#     #             action_type=ActionRight.CREATE,
#     #             action_count_customer_level=1,
#     #             head=True,
#     #             policy_rule_id=policy_rule.id,
#     #             action_by=str(user.id),created_at=None,updated_at=None, preceding_action_id=None,succeeding_action_id=None,rating_instance_id=None

#     #         )
#     #         # initial_step = WorkflowAction(**initial_workflow_data.model_dump())
#     #         initial_step = WorkflowAction(**initial_workflow_data.__dict__)
#     #         db.add(initial_step)
#     #         db.commit()





#     #         cloned_wf = initial_workflow_data.clone()
#     #         processed_workflow_data=  WorkflowAction(**cloned_wf,id=uuid4()) # no need to clone this

#     #     # db.add(processed_workflow_data)
#     #     # initial_step.head=False
#     #     # db.add(initial_step)
#     #     # db.flush()
#     #         db.commit()
#     #     # initial_step.succeeding_action_id=processed_workflow_data.id 

#     #     #check if rights to submit

#     #     # Check Submit rights

#     #     else:
#     #         raise ValueError(f"User {user.name} does not have required maker role for this policy")




#     #     Simulate a review
#     # reviewer = User(id=uuid4(), name="reviewer",password=get_hashed_password('1234'),
#     #                 email="reviewer@example.com", role="reviewer")
#     # db.add(reviewer)
#     # db.commit()
#     # review_wf = WorkflowActionSchema.model_validate(processed_workflow_data).clone()
#     # review_workflow_data=  WorkflowActionSchema(**review_wf,id=uuid4()) # no need to clone this
#     # db.add(WorkflowAction(**review_workflow_data.model_dump()))
#     # db.commit()
