
import uuid

from click import edit
from fastapi import HTTPException
from config import DB_NAME, create_engine_and_session
from models.policy_rules_model import PolicyRule, RatingAccessRule
from enums_and_constants import EditFlow, WorkflowStage,RejectionFlow
from logging import raiseExceptions
from typing import List, Tuple
from uuid import UUID, uuid4

from calculate_derived_scores import calculate_derived_scores
from dependencies import auth_handler, ensure_uuid
from enums_and_constants import ActionRight, WorkflowErrorCode
from models.models import Customer, Role, User
from models.rating_instance_model import RatingFactorScore, RatingInstance
from models.rating_model_model import RatingModel, RatingModelApplicabilityRules, ScoreToGradeMapping
from models.statement_models import FinancialStatement, Template
from models.workflow_model import WorkflowAction
from rating_model import configure_rating_model_factors, get_or_create_rating_model
# from rating_model_instance import (
#     check_all_user_inputs_factor_availability,
#     get_quant_factor_inputs,
#     score_quantitative_factors,
#     update_qualitative_factor_scores,
# )
from rating_model_instance import (
    check_all_user_inputs_factor_availability,
)
from rating_model_instance import (
    score_quantitative_factors,
)
from rating_model_instance import (
    update_qualitative_factor_scores,
)
from rating_model_instance import (
    get_quant_factor_inputs,
)
from schema.schema import RatingFactorScore as RatingFactorScoreSchema, RatingModelApplicabilityRulesCreate
from schema.schema import (
    RatingFactorScoreCreate,
    RatingInstanceCreate,
    WorkflowActionCreate,
)
from schema.schema import User as UserSchema
from schema.schema import WorkflowAction as WorkflowActionSchema
from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from schema.schema import WorkflowError
from schema.schema import ErrorResponse
from security import get_hashed_password
from schema import schema

# def clone_rating_instance(db: Session, original_instance: RatingInstanceCreate, new_workflow_step: WorkflowActionSchema) -> schema.RatingInstance:

from rating_model_instance import generate_qualitative_factor_data

def create_rating_instance_for_initial_step(wf_data:WorkflowAction,rating_model_id:UUID, statement_id:UUID,user:User, db:Session):
            customer_id=wf_data.customer_id
                # Create initial rating instance with validation
            instance_data = RatingInstanceCreate(
                id=uuid4(),
                customer_id=ensure_uuid(customer_id),
                financial_statement_id=ensure_uuid(statement_id),
                rating_model_id=rating_model_id,
                workflow_action_id=wf_data.id,
                overall_status=WorkflowStage.MAKER
            )
            initial_rating_instance = RatingInstance(**instance_data.model_dump())
            db.add(initial_rating_instance)
            db.add(wf_data)
            wf_data.rating_instance_id = initial_rating_instance.id
            db.commit()
            generate_qualitative_factor_data(db,initial_rating_instance)
            # Process the rating instance
            processed_instance = process_rating_instance(
                db, initial_rating_instance, user)
            return processed_instance

def process_rating_instance(db: Session, rating_instance: RatingInstance, user: UserSchema):
    """Process a rating instance and create a new workflow step"""
    try:
        # rating_instance.overall_status = ActionRight.SUBMITTED
        
        # Process the rating
        quant_factor_scores, incomplete_financial_information, missing_fields = get_quant_factor_inputs(
            db, rating_instance)

        if incomplete_financial_information:
            rating_instance.incomplete_financial_information = True
            rating_instance.missing_financial_fields = missing_fields
            db.commit()
            return rating_instance

        if check_all_user_inputs_factor_availability(db, rating_instance):
            score_quantitative_factors(db, rating_instance)
            update_qualitative_factor_scores(db, rating_instance)
            calculate_derived_scores(db, rating_instance)
            
            db.commit()
            return rating_instance
        
        return rating_instance

    except Exception as e:
        print(f"Error processing rating instance: {str(e)}")
        db.rollback()
        raise
def create_rating_workflow_for_customer(db: Session, customer: Customer, user: User):
    try:
        # Check policy rule
        
        policy_rule = get_policy_rules_for_customer(cif_number=None, customer_id=customer.id,db=db)
        if not policy_rule:
            raise WorkflowError(
                code=WorkflowErrorCode.POLICY_RULE_NOT_FOUND,
                details={"customer_id": str(customer.id)}
            )

        # Get maker stage access rules for the user
        maker_access_rules = RatingAccessRule.get_user_access(
            db,
            policy_id=policy_rule.id,
            user_id=user.id,
            workflow_stage=WorkflowStage.MAKER
        )

        # Check if user has any maker roles
        if not maker_access_rules:
            # Get all maker roles for error message
            all_maker_roles = (
                db.query(RatingAccessRule.role_name)
                .filter(
                    RatingAccessRule.policy_id == policy_rule.id,
                    RatingAccessRule.workflow_stage == WorkflowStage.MAKER
                )
                .distinct()
                .all()
            )
            allowed_role_names = [role[0] for role in all_maker_roles]
            
            raise WorkflowError(
                code=WorkflowErrorCode.UNAUTHORIZED_ROLE,
                details={"user_roles": user.role, "required_roles": allowed_role_names}
            )

        # Check existing workflow
        # if check_if_existing_workflow_for_customer(customer_id=customer.id):
        #     raise WorkflowError(code=WorkflowErrorCode.WORKFLOW_EXISTS)

        # Check creation rights
        if not any(ActionRight.CREATE in rule.action_rights for rule in maker_access_rules):
            raise WorkflowError(
                code=WorkflowErrorCode.UNAUTHORIZED_ACTION,
                details={"action": "CREATE"}
            )

        # Create workflow
        workflow_cycle_id = uuid4()
        initial_workflow = WorkflowAction(
            id=uuid4(),
            workflow_cycle_id=workflow_cycle_id,
            customer_id=customer.id,
            workflow_stage=WorkflowStage.MAKER,
            action_type=ActionRight.INIT,
            action_count_customer_level=1,
            head=True,
            is_stale=False,
            policy_rule_id=policy_rule.id,
            user_id=user.id,
            preceding_action_id=None,
            succeeding_action_id=None
        )
        
        db.add(initial_workflow)
        
        # Get financial statement
        statement = db.query(FinancialStatement).filter(
            FinancialStatement.customer_id == customer.id,
            FinancialStatement.financials_period_year == 2023
        ).first()
        
        if not statement:
            raise WorkflowError(
                code=WorkflowErrorCode.STATEMENT_NOT_FOUND,
                details={"customer_id": str(customer.id), "year": 2023}
            )

        db.commit()
        return initial_workflow

    except WorkflowError as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        raise WorkflowError(
            code=WorkflowErrorCode.UNAUTHORIZED_ACTION,
            message=f"Unexpected error: {str(e)}"
        )

# Helper methods for workflow creation
def create_complete_rating_workflow(db: Session, customer: Customer, user: User) -> RatingInstance:
    """Create complete workflow including initial step and rating instance"""
    try:
        # Create initial workflow step
        initial_step = create_rating_workflow_for_customer(db, customer=customer, user=user)
        
        # Get rating model
        rating_model_id = get_applicable_rating_model_for_business_unit(
            db, 
            customer.business_unit_id
        )
        
        # Get financial statement
        statement = db.query(FinancialStatement).filter(
            FinancialStatement.customer_id == customer.id,
            FinancialStatement.financials_period_year == 2023
        ).first()
        
        if not statement:
            raise WorkflowError(
                code=WorkflowErrorCode.STATEMENT_NOT_FOUND,
                details={"customer_id": str(customer.id), "year": 2023}
            )
            
        # Create rating instance
        rating_instance = create_rating_instance_for_initial_step(
            initial_step,
            rating_model_id,
            statement.id,
            user,
            db
        )
        
        return rating_instance
        
    except Exception as e:
        db.rollback()
        if isinstance(e, WorkflowError):
            raise e
        raise WorkflowError(
            code=WorkflowErrorCode.WORKFLOW_CREATION_FAILED,
            message=f"Failed to create complete workflow: {str(e)}"
        )

# # Example usage in route
# @router.post("/ratings/create/{customer_id}")
# async def create_rating(
#     customer_id: UUID,
#     current_user: User = Depends(auth_handler.auth_wrapper),
#     db: Session = Depends(get_db)
# ):
#     customer = db.query(Customer).filter(Customer.id == customer_id).first()
#     if not customer:
#         raise HTTPException(status_code=404, detail="Customer not found")
        
#     try:
#         rating_instance = create_complete_rating_workflow(
#             db=db,
#             customer=customer,
#             user=current_user
#         )
        
#         return {
#             "message": "Rating workflow created successfully",
#             "rating_instance_id": str(rating_instance.id),
#             "workflow_id": str(rating_instance.workflow_actions[0].id)
#         }
        
#     except WorkflowError as e:
#         raise HTTPException(
#             status_code=400,
#             detail={
#                 "code": e.code,
#                 "message": e.message,
#                 "details": e.details
#             }
#         )
def get_policy_rules_for_customer(cif_number: str|None, customer_id:str|UUID,db:Session)-> PolicyRule|None:
    if cif_number:
        customer = db.query(Customer).options(joinedload(Customer.business_unit)).filter(Customer.cif_number==cif_number).first()
    else:
        customer = db.query(Customer).options(joinedload(Customer.business_unit)).filter(Customer.id==customer_id).first()
    if customer:
        policy_rule=db.query(PolicyRule).filter(PolicyRule.business_unit_id==customer.business_unit_id).first()
        return policy_rule
    else:
        return None


def get_policy_rules_by_id(policy_id:UUID)->PolicyRule|None:
    policy=db.query(PolicyRule).filter(PolicyRule.id==policy_id).first()
    return policy


def get_applicable_rating_model_for_business_unit(db:Session,business_unit_id:UUID)-> UUID | None:
    rating_model= db.query(RatingModelApplicabilityRules).filter(RatingModelApplicabilityRules.business_unit_id==business_unit_id).first()
    # rating_model=schema.RatingModel(**rating_model.__dict__)
    if rating_model and rating_model.rating_model_id:
        return rating_model.rating_model_id
    else:
        return None
    


if __name__ == "__main__":
    from customer_financial_statement import FsApp
    from main import init_db
    from rating_model_instance import generate_qualitative_factor_data
    from security import AuthHandler, RequiresLoginException
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker,joinedload
    from schema.schema import RatingModelApplicabilityRulesCreate
    from schema.schema import RatingModelApplicabilityRules as RatingModelApplicabilityRulesSchema
    from models import rating_model_model
    init_db(DB_NAME)
    _, db = create_engine_and_session(DB_NAME)
    configure_rating_model_factors(db)
    app = FsApp(db)
    cif_number="CIF-123456"
    customer = app.create_statement_data_for_customer(cif_number)
    print(f"Created statement data for customer: {customer.customer_name}")

    template = db.query(Template).filter(
        Template.name == "FinTemplate").first()
    rating_model = get_or_create_rating_model(
        session=db, template=template, model_name='Corporate')
    customer = db.query(Customer).options(joinedload(Customer.business_unit)).filter(Customer.cif_number=='CIF-123456').first()
    if rating_model:
        ratingModelApplicable=RatingModelApplicabilityRulesCreate(rating_model=rating_model,rating_model_id=rating_model.id,business_unit=customer.business_unit,business_unit_id=customer.business_unit.id)

        from models.rating_model_model import RatingModelApplicabilityRules
        # db.add(rating_model_model.RatingModelApplicabilityRules(**ratingModelApplicable.__dict__))
    # Use exclude to remove the relationship fields
        db.add(rating_model_model.RatingModelApplicabilityRules(**ratingModelApplicable.model_dump(exclude={'rating_model', 'business_unit'})))
        db.commit()
    # create_default_policy(db,default_policy, customer.business_unit)
    # Create score to grade mappings
    mapping_data: List[Tuple[float, float, int]] = [
        (float('-inf'), 0.50, 12),
        (0.50, 1.10, 11),
        (1.10, 1.60, 11),
        (1.60, 2.10, 11),
        (2.10, 2.60, 10),
        (2.60, 3.10, 10),
        (3.10, 3.60, 10),
        (3.60, 4.00, 9),
        (4.00, 4.50, 9),
        (4.50, 5.00, 9),
        (5.00, 5.50, 8),
        (5.50, 6.00, 8),
        (6.00, 6.40, 7),
        (6.40, 6.80, 7),
        (6.80, 7.20, 6),
        (7.20, 7.60, 5),
        (7.60, 8.00, 4),
        (8.00, 8.40, 3),
        (8.40, 8.80, 2),
        (8.80, 10.00, 1)
    ]

    mappings = [
        ScoreToGradeMapping(
            rating_model_id=rating_model.id,
            bin_start=start,
            bin_end=end,
            grade=str(grade)
        )
        for start, end, grade in mapping_data
    ]

    db.add_all(mappings)
    db.commit()
    
    auth_handler=AuthHandler()

    user=db.query(User).filter(User.email=='ashley.cherian@gmail.com').first()

    customer=db.query(Customer).filter(Customer.cif_number==cif_number).first()
    #identify the rating model to be used for a business unit
    initial_step=create_rating_workflow_for_customer(db,customer=customer,user=user)
    rating_model_id= get_applicable_rating_model_for_business_unit(db,customer.business_unit_id)
            # Get a financial statement
    statement = db.query(FinancialStatement).filter(
                FinancialStatement.customer_id == customer.id).filter(FinancialStatement.financials_period_year==2023).first()
    rating_instance = create_rating_instance_for_initial_step(initial_step,rating_model_id,statement.id,user,db) 




