from logging import raiseExceptions
import uuid
from sqlalchemy.orm import Session
from models.rating_model_model import ScoreToGradeMapping
from models.statement_models import Template
from models.workflow_model import WorkflowAction
from models.rating_instance_model import RatingFactorScore
from models.rating_model_model import RatingModel
from models.statement_models import FinancialStatement
from models.rating_instance_model import RatingInstance
from models.models import (
    User, Customer
)
from schema.schema import (
    WorkflowAction as WorkflowActionSchema,
    WorkflowActionCreate,
    RatingInstanceCreate,
    RatingFactorScoreCreate,
    User as UserSchema,
    RatingFactorScore as RatingFactorScoreSchema
)
from typing import List, Tuple
from uuid import uuid4
from sqlalchemy import and_
from schema.schema import WorkflowStatus
from uuid import UUID
from rating_model import configure_rating_model_factors, get_or_create_rating_model
from rating_model_instance import (
    get_quant_factor_inputs, score_quantitative_factors,
    update_qualitative_factor_scores, check_all_user_inputs_factor_availability
)
from calculate_derived_scores import calculate_derived_scores
from dependencies import auth_handler

from uuid import uuid4
import bcrypt

def create_workflow_action(db: Session, customer_id: UUID, action_type: WorkflowStatus, action_by: UserSchema) -> WorkflowAction:

    latest_step = db.query(WorkflowAction).filter(
        WorkflowAction.customer_id == customer_id
    ).order_by(WorkflowAction.action_count_customer_level.desc()).first()

    # Validate using Pydantic schema
    workflow_data = WorkflowActionCreate(
        id=uuid4(),
        customer_id=customer_id,
        action_type=action_type,
        description=f"{action_type.value} step",
        action_count_customer_level=(
            latest_step.action_count_customer_level + 1) if latest_step else 1,
        action_by=action_by.id,
        head=True
    )
    new_step = WorkflowAction(**workflow_data.model_dump())
    db.add(new_step)
    db.flush()
    return new_step


def clone_rating_instance(db: Session, original_instance: RatingInstanceCreate, new_workflow_step: WorkflowActionSchema) -> RatingInstance:
    # Validate using Pydantic schema
    instance_data = RatingInstanceCreate(
        id=uuid4(),
        customer_id=original_instance.customer_id,
        financial_statement_id=original_instance.financial_statement_id,
        rating_model_id=original_instance.rating_model_id,
        workflow_action_id=new_workflow_step.id,
        overall_status=new_workflow_step.action_type,
        incomplete_financial_information=original_instance.incomplete_financial_information,
        missing_financial_fields=original_instance.missing_financial_fields,
        overall_score=original_instance.overall_score,
        overall_rating=original_instance.overall_rating
    )

    new_instance = RatingInstance(**instance_data.model_dump())
    db.add(new_instance)
    db.flush()

    # Clone and validate factor scores
    for score in db.query(RatingFactorScore).filter(RatingFactorScore.rating_instance_id == original_instance.id).all():
        score_data = RatingFactorScoreCreate(
            rating_instance_id=new_instance.id,
            rating_factor_id=score.rating_factor_id,
                raw_value_text=score.raw_value_text,
                raw_value_float= score.raw_value_float,
                score= score.score
            
        )
        new_score = RatingFactorScore(**score_data.model_dump())
        db.add(new_score)
        db.commit()
    return new_instance


def process_rating_instance(db: Session, rating_instance: RatingInstance, user: UserSchema):
    """Process a rating instance and create a new workflow step"""
    try:
        rating_instance.overall_status = WorkflowStatus.SUBMITTED
        
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

def get_current_workflow_status(rating_instance: RatingInstance) -> WorkflowStatus:
    """Get the current workflow status from the most recent action"""
    current_action = rating_instance.current_workflow_action
    return current_action.action_type if current_action else WorkflowStatus.DRAFT

def get_workflow_history(db: Session, rating_instance_id: UUID) -> List[WorkflowAction]:
    """Get all workflow actions for a rating instance in chronological order"""
    return db.query(WorkflowAction)\
        .filter(WorkflowAction.rating_instance_id == rating_instance_id)\
        .order_by(WorkflowAction.action_count_customer_level)\
        .all()

def review_rating_instance(db: Session, rating_instance: RatingInstance, workflow_id:UUID, reviewer: User, approved: bool, comments: str):
    """Review a rating instance and create appropriate workflow actions"""
    try:
        # Create a new workflow action for the review
        review_status = WorkflowStatus.APPROVED if approved else WorkflowStatus.REJECTED
        
        # workflow_step = WorkflowAction(
        #     id=uuid4(),
        #     customer_id=rating_instance.customer_id,
        #     action_type=review_status,
        #     action_by=reviewer.id,
        #     rating_instance_id=rating_instance.id,
        #     action_count_customer_level=len(rating_instance.workflow_actions) + 1,
        #     description=comments,
        #     preceding_action_id=rating_instance.current_workflow_action.id if rating_instance.current_workflow_action else None
        # )
        workflow= db.query(WorkflowAction).filter(WorkflowAction.id==workflow_id)
        #clone rating instance here
        # db.add(workflow_step)
        rating_instance.overall_status = review_status
        
        db.commit()
        return rating_instance

    except Exception as e:
        print(f"Error reviewing rating instance: {str(e)}")
        db.rollback()
        raise
def get_hashed_password(password: str) -> str:
        # Convert the password to bytes
        password_bytes = password.encode('utf-8')
        # Generate a salt and hash the password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        # Return the hash as a string
        return hashed.decode('utf-8')
def create_default_users(session: Session) -> None:
    """
    Create default users with various role combinations using UserSchema
    """
    # Define default users with their roles
    default_users = [
        UserSchema(
            id=uuid4(),
            name="ashley",
            password=get_hashed_password('admin'),
            email="ashley.cherian@gmail.com",
            role=["creator"],
            created_at=None,
            updated_at=None
        ),
        UserSchema(
            id=uuid4(),
            name="John Smith",
            password=get_hashed_password('admin'),
            email="john.smith@example.com",
            role=["Credit Analyst"],
            created_at=None,
            updated_at=None
        ),
        UserSchema(
            id=uuid4(),
            name="Sarah Johnson",
            password=get_hashed_password('admin'),
            email="sarah.johnson@example.com",
            role=["Relationship Manager"],
            created_at=None,
            updated_at=None
        ),
        UserSchema(
            id=uuid4(),
            name="Michael Chen",
            password=get_hashed_password('admin'),
            email="michael.chen@example.com",
            role=["BU Head"],
            created_at=None,
            updated_at=None
        ),
        UserSchema(
            id=uuid4(),
            name="James Martinez",
            password=get_hashed_password('admin'),
            email="james.martinez@example.com",
            role=["Credit Analyst", "Relationship Manager"],
            created_at=None,
            updated_at=None
        ),
        UserSchema(
            id=uuid4(),
            name="Rachel Lee",
            password=get_hashed_password('admin'),
            email="rachel.lee@example.com",
            role=["BU Head", "Country Head"],
            created_at=None,
            updated_at=None
        ),
        UserSchema(
            id=uuid4(),
            name="David Wilson",
            password=get_hashed_password('admin'),
            email="david.wilson@example.com",
            role=["CRO"],
            created_at=None,
            updated_at=None
        ),
        UserSchema(
            id=uuid4(),
            name="Lisa Anderson",
            password=get_hashed_password('admin'),
            email="lisa.anderson@example.com",
            role=["CEO"],
            created_at=None,
            updated_at=None
        )
    ]

    # Add the users to the database
    for user_schema in default_users:
        db.add(User(**user_schema.model_dump()))
    
    db.commit()
if __name__ == "__main__":
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from main import create_engine_and_session, DB_NAME, init_db
    from customer_financial_statement import FsApp
    from rating_model_instance import generate_qualitative_factor_data

    from security import AuthHandler, RequiresLoginException
    init_db(DB_NAME)
    _, db = create_engine_and_session(DB_NAME)
    configure_rating_model_factors(db)
    app = FsApp(db)
    customer = app.create_statement_data_for_customer("CIF-123456")
    print(f"Created statement data for customer: {customer.customer_name}")

    template = db.query(Template).filter(
        Template.name == "FinTemplate").first()
    rating_model = get_or_create_rating_model(
        session=db, template=template, model_name='Corporate')

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

    # Create a user
    
    # user = UserSchema(id=uuid4(), name="ashley",password=get_hashed_password('admin'),
    #             email="ashley.cherian@gmail.com", role=[]"creator",created_at=None,updated_at=None)
    # db.add(User(**user.model_dump()))
    # db.commit()
    create_default_users(db)
    user=db.query(User).filter(User.email=='ashley.cherian@gmail.com').first()
    work_flow_cycle_id=uuid4()
    # Create initial workflow step with validation
    initial_workflow_data = WorkflowActionSchema(
        id=uuid4(),
        workflow_cycle_id=work_flow_cycle_id,
        customer_id=customer.id,
        action_type=WorkflowStatus.DRAFT,
        action_count_customer_level=1,
        head=True,
        action_by=str(user.id),created_at=None,updated_at=None, preceding_action_id=None,succeeding_action_id=None,rating_instance_id=None

    )
    initial_step = WorkflowAction(**initial_workflow_data.model_dump())
    db.add(initial_step)
    db.commit()

    # Get a financial statement
    statement = db.query(FinancialStatement).filter(
        FinancialStatement.customer_id == customer.id).filter(FinancialStatement.financials_period_year==2023).first()

    # Create initial rating instance with validation
    instance_data = RatingInstanceCreate(
        id=uuid4(),
        customer_id=customer.id,
        financial_statement_id=statement.id,
        rating_model_id=rating_model.id,
        # workflow_action_id=initial_step.id,
        overall_status=WorkflowStatus.DRAFT
    )
    initial_rating_instance = RatingInstance(**instance_data.model_dump())
    db.add(initial_rating_instance)
    initial_workflow_data.rating_instance_id = initial_rating_instance.id
    db.commit()
    generate_qualitative_factor_data(db,initial_rating_instance)
    # Process the rating instance
    processed_instance = process_rating_instance(
        db, initial_rating_instance, user)

    cloned_wf = initial_workflow_data.clone()
    processed_workflow_data=  WorkflowAction(**cloned_wf,id=uuid4()) # no need to clone this

    db.add(processed_workflow_data)
    initial_step.head=False
    db.add(initial_step)
    db.flush()
    db.commit()
    # initial_step.succeeding_action_id=processed_workflow_data.id 
    db.commit()
    
    # Simulate a review
    reviewer = User(id=uuid4(), name="reviewer",password=get_hashed_password('1234'),
                    email="reviewer@example.com", role="reviewer")
    db.add(reviewer)
    db.commit()
    review_wf = WorkflowActionSchema.model_validate(processed_workflow_data).clone()
    review_workflow_data=  WorkflowActionSchema(**review_wf,id=uuid4()) # no need to clone this
    db.add(WorkflowAction(**review_workflow_data.model_dump()))
    db.commit()
    # db.add(processed_workflow_data)
    # db.commit()
    
    
    # reviewed_instance = review_rating_instance(
    #     db, process_rating_instance, review_workflow_data.id, reviewer, approved=True, comments="Looks good, ready for approval.")

    # # Get rating instance history
    # history = get_rating_instance_history(db, customer.id)
    # print(f"Rating instance history count: {len(history)}")

    # # Get current rating instance
    # current_instance = get_current_rating_instance(db, customer.id)

    # print(f"Current rating instance status: {current_instance.overall_status}")
