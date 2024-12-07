
from pathlib import Path
from fastapi import Depends
from fastapi.testclient import TestClient
from typing import List, Tuple
import sys
from os import getenv
import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker



# sys.path.insert(1, "/home/ashleyubuntu/ratingModelPython/backend")
from app import app
from config import DB_NAME, create_engine_and_session
from enums_and_constants import ActionRight, WorkflowErrorCode, WorkflowStage
from models.rating_model_model import FactorInputSource, ScoreToGradeMapping
from models.rating_instance_model import RatingFactorScore
from models.rating_model_model import RatingFactor, RatingModel
from models.statement_models import FinancialStatement
from models.rating_instance_model import RatingInstance
from models.workflow_model import WorkflowAction
from rating_workflow_processing import create_rating_instance_for_initial_step, create_rating_workflow_for_customer, get_applicable_rating_model_for_business_unit
from schema import schema
client = TestClient(app)
# SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@localhost/llama_app_db"

# engine = create_engine(SQLALCHEMY_DATABASE_URL)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from schema import schema
from models import models



import pprint


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.statement_models import Template
from schema import schema

from main import init_db
from customer_financial_statement import FsApp
from models.rating_instance_model import RatingInstance
from rating_model import configure_rating_model_factors, get_or_create_rating_model

from   rating_model_instance import get_quant_factor_inputs

from main import init_db
from rating_model_instance import generate_qualitative_factor_data
from security import AuthHandler, RequiresLoginException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,joinedload
from schema.schema import RatingModelApplicabilityRulesCreate, WorkflowError
from schema.schema import RatingModelApplicabilityRules as RatingModelApplicabilityRulesSchema
from models import rating_model_model
from dependencies import get_db



@pytest.fixture
def workflow_test_data():
    db=next(get_db())
    init_db(DB_NAME)
    # _, db = create_engine_and_session(DB_NAME)
    configure_rating_model_factors(db)
    app = FsApp(db)
    cif_number="CIF-123456"
    customer = app.create_statement_data_for_customer(cif_number)
    print(f"Created statement data for customer: {customer.customer_name}")

    template = db.query(Template).filter(
        Template.name == "FinTemplate").first()
    rating_model = get_or_create_rating_model(
        session=db, template=template, model_name='Corporate')
    customer = db.query(models.Customer).options(joinedload(models.Customer.business_unit)).filter(models.Customer.cif_number=='CIF-123456').first()
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

    user=db.query(models.User).filter(models.User.email=='ashley.cherian@gmail.com').first()

    customer=db.query(models.Customer).filter(models.Customer.cif_number==cif_number).first()
    #identify the rating model to be used for a business unit
    initial_step=create_rating_workflow_for_customer(db,customer=customer,user=user)
    rating_model_id= get_applicable_rating_model_for_business_unit(db,customer.business_unit_id)
            # Get a financial statement
    statement = db.query(FinancialStatement).filter(
                FinancialStatement.customer_id == customer.id).filter(FinancialStatement.financials_period_year==2023).first()
    rating_instance = create_rating_instance_for_initial_step(initial_step,rating_model_id,statement.id,user,db) 

    assert  rating_instance.id is not None
    return initial_step


@pytest.fixture
def db():
    """Provide a database session for tests"""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def auth_client():
    """Returns an authenticated client"""
    response = client.post(
        "/login/",
        data={
            "email": "ashley.cherian@gmail.com",
            "password": "admin"
        }
    )
    assert response.status_code == 303  # Redirect status
    assert "Authorization" in response.cookies
    return response.cookies["Authorization"]
    
def test_login_success():
    """Test successful submission of a rating by an analyst"""
    # Login as analyst

    login_response = client.post(
        "/login_new",
        data={"email": "ashley.cherian@gmail.com", "password": "admin","testing":'True'},allow_redirects=False
    )
    assert login_response.status_code == 200
    assert login_response.cookies["Authorization"]
    auth_cookie = login_response.cookies.get("Authorization")


def test_if_workflow_stage_is_at_maker(workflow_test_data):
    workflow_action= workflow_test_data
    assert workflow_action.workflow_stage==WorkflowStage.MAKER


def test_submission_by_maker_delete(workflow_test_data):
    workflow_action= workflow_test_data
    assert workflow_action.workflow_stage==WorkflowStage.MAKER
    login_response = client.post(
        "/login",
        data={"email": "ashley.cherian@gmail.com", "password": "admin","testing":'True'},allow_redirects=False
    )
    assert login_response.status_code == 200
    auth_cookie = login_response.cookies.get("Authorization")
    db=next(get_db())
    rating_instance_id=workflow_action.rating_instance_id
    wf_id= workflow_action.id
    # response = client.post(
    #     f"/submit_rating/{rating_instance_id}/{wf_id}",allow_redirects=False
    # )
    # assert response.status_code==200
    
    # Verify workflow is in MAKER stage
    assert workflow_action.workflow_stage == WorkflowStage.MAKER
    
    # Submit rating with auth cookie
    response = client.post(
        f"/rating/{rating_instance_id}/{workflow_action.id}",
        cookies={"Authorization": auth_cookie},
        allow_redirects=False
    )
    
    # Print debug information
    print(f"Response status code: {response.status_code}")
    if response.status_code != 303:
        print(f"Response content: {response.text}")
    
    assert response.status_code == 303  # Expecting redirect


from fastapi.testclient import TestClient
from app import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
      yield c

@pytest.fixture(scope="module")
def test_user():
    email="ashley.cherian@gmail.com"

    return {
        # "id": str(user.id),  # Convert UUID to string
        "email":email , 
        "password": "admin",
        "testing": "true"
    }


@pytest.fixture(scope="module")
def test_credit_analyst_user():
    email= "john.smith@example.com"
    # db = next(get_db())
    # user = db.query(models.User).filter(models.User.email ==email).first()
    # if user:
    return {
        # "id": str(user.id),  # Convert UUID to string
        "email":email , 
        "password": "admin",
        "testing": "true"
    }

@pytest.fixture(scope="module")
def test_approver_1_user():

    email= "rachel.lee@example.com"
    return {
        # "id": str(user.id),  # Convert UUID to string
        "email":email , 
        "password": "admin",
        "testing": "true"
    }

@pytest.fixture(scope="module")
def test_approver_2_user():

    email= "david.wilson@example.com"
    return {
        # "id": str(user.id),  # Convert UUID to string
        "email":email , 
        "password": "admin",
        "testing": "true"
    }

@pytest.fixture(scope="module")
def test_approver_3_user():
    email= "lisa.anderson@example.com"
    return {
        # "id": str(user.id),  # Convert UUID to string
        "email":email , 
        "password": "admin",
        "testing": "true"
    }

def test_login(client, test_user):
    login_response = client.post("/login", data=test_user)
    assert login_response.status_code == 200
    auth_cookie = login_response.cookies.get("Authorization")
    assert auth_cookie is not None
    return auth_cookie

def test_submission_by_maker(client, test_user, workflow_test_data):
    auth_cookie = test_login(client, test_user)
    workflow_action = workflow_test_data
    assert workflow_action.workflow_stage == WorkflowStage.MAKER
    
    response = client.post(
        f"/submit_rating/{workflow_action.rating_instance_id}/{workflow_action.id}",
        cookies={"Authorization": auth_cookie},
        allow_redirects=False
    )

    db = next(get_db())
    all_workflow_actions = db.query(WorkflowAction).filter(
        WorkflowAction.workflow_cycle_id == workflow_action.workflow_cycle_id
    ).order_by(WorkflowAction.created_at).all()

    print(all_workflow_actions)

    # Check total number of actions
    assert len(all_workflow_actions) == 3

    # Check first action
    assert all_workflow_actions[0].workflow_stage == WorkflowStage.MAKER
    assert all_workflow_actions[0].action_type == ActionRight.CREATE

    # Check second action
    assert all_workflow_actions[1].workflow_stage == WorkflowStage.MAKER
    assert all_workflow_actions[1].action_type == ActionRight.APPROVE

    # Check third action
    assert all_workflow_actions[2].workflow_stage == WorkflowStage.CHECKER
    assert all_workflow_actions[2].action_type== ActionRight.MOVE_TO_NEXT_STAGE

    # Additional checks if needed
    assert workflow_action.rating_instance_id == all_workflow_actions[2].rating_instance_id
    assert workflow_action.workflow_cycle_id == all_workflow_actions[2].workflow_cycle_id
 


def test_submission_by_checker(client, test_user, test_credit_analyst_user, workflow_test_data):
    # Initial setup - maker approval

    db = next(get_db())
    maker_auth_cookie = test_login(client, test_user)
    test_user_id = db.query(models.User).filter(models.User.email == test_user['email']).first()
    test_credit_analyst_user_id = db.query(models.User).filter(models.User.email == test_credit_analyst_user['email']).first()
    workflow_action = workflow_test_data
    assert workflow_action.workflow_stage == WorkflowStage.MAKER
    
    # Submit as maker
    maker_response = client.post(
        f"/submit_rating/{workflow_action.rating_instance_id}/{workflow_action.id}",
        cookies={"Authorization": maker_auth_cookie},
        allow_redirects=False
    )
    assert maker_response.status_code == 303
    
    # Get checker action step
    checker_action_step = (db.query(WorkflowAction)
        .filter(WorkflowAction.workflow_cycle_id == workflow_action.workflow_cycle_id)
        .filter(WorkflowAction.workflow_stage == WorkflowStage.CHECKER)
        .first())
    
    # Submit as checker
    checker_auth_cookie = test_login(client, test_credit_analyst_user)
    checker_response = client.post(
        f"/submit_rating/{checker_action_step.rating_instance_id}/{checker_action_step.id}",
        cookies={"Authorization": checker_auth_cookie},
        allow_redirects=False
    )
    assert checker_response.status_code == 303
    
    # Get all workflow actions in order
    db = next(get_db())
    all_workflow_actions = (
        db.query(WorkflowAction)
        .filter(WorkflowAction.workflow_cycle_id == workflow_action.workflow_cycle_id)
        .order_by(WorkflowAction.action_count_customer_level)
        .all()
    )
    
    # Verify the complete sequence
    assert len(all_workflow_actions) == 7  # Total number of steps
    
    # Check each step in the sequence
    steps = [
        # Initial maker step
        {"stage": WorkflowStage.MAKER, "action_type": ActionRight.INIT, "user_id": test_user_id.id},
        # Maker approval
        {"stage": WorkflowStage.MAKER, "action_type": ActionRight.APPROVE, "user_id": test_user_id.id},
        # Exit maker stage
        {"stage": WorkflowStage.MAKER, "action_type": ActionRight.EXIT, "user_id": None},
        # Init checker stage
        {"stage": WorkflowStage.CHECKER, "action_type": ActionRight.INIT, "user_id": None},
        # Checker approval
        {"stage": WorkflowStage.CHECKER, "action_type": ActionRight.APPROVE, "user_id": test_credit_analyst_user_id.id},
        # Exit checker stage
        {"stage": WorkflowStage.CHECKER, "action_type": ActionRight.EXIT, "user_id": None},
        # Init approver stage
        {"stage": WorkflowStage.APPROVER, "action_type": ActionRight.INIT, "user_id": None}
    ]
    
    for i, expected in enumerate(steps):
        action = all_workflow_actions[i]
        assert action.workflow_stage == expected["stage"], f"Step {i+1}: Wrong stage"
        assert action.action_type == expected["action_type"], f"Step {i+1}: Wrong action type"
        assert action.user_id == expected["user_id"], f"Step {i+1}: Wrong user"
        
        # Check head and stale flags
        if i == len(steps) - 1:  # Last step should be head and not stale
            assert action.head == True
            assert action.is_stale == False
        else:  # All other steps should not be head and should be stale
            assert action.head == False
            assert action.is_stale == True
            
        # Verify action counts are sequential
        assert action.action_count_customer_level == i + 1

def test_submission_by_unauthorized_role(client, test_credit_analyst_user, workflow_test_data):
    """Test submission by a user without proper role permissions"""
    # Login as unauthorized user
    auth_cookie = test_login(client, test_credit_analyst_user)
    workflow_action = workflow_test_data
    
    # Attempt to submit rating
    response = client.post(
        f"/submit_rating/{workflow_action.rating_instance_id}/{workflow_action.id}",
        cookies={"Authorization": auth_cookie},
        allow_redirects=False
    )
    error = WorkflowError.model_validate(response.json()) 
    assert error.code == WorkflowErrorCode.UNAUTHORIZED_ROLE

def test_double_submission_by_same_user(client, test_user, workflow_test_data):
    """Test that same user cannot submit twice"""
    auth_cookie = test_login(client, test_user)
    workflow_action = workflow_test_data
    
    # First submission
    response1 = client.post(
        f"/submit_rating/{workflow_action.rating_instance_id}/{workflow_action.id}",
        cookies={"Authorization": auth_cookie},
        allow_redirects=False
    )
    assert response1.status_code == 303
    
    # Second submission attempt
    response2 = client.post(
        f"/submit_rating/{workflow_action.rating_instance_id}/{workflow_action.id}",
        cookies={"Authorization": auth_cookie},
        allow_redirects=False
    )
    error = WorkflowError.model_validate(response2.json()) 
    assert error.code == WorkflowErrorCode.ALREADY_SUBMITTED




def test_submission_by_approver(client, test_user, test_credit_analyst_user, workflow_test_data, 
                            test_approver_1_user, test_approver_2_user, test_approver_3_user,db):
    # Get database session
    # db = next(get_db())
    maker_auth_cookie = test_login(client, test_user)
    test_user_id = db.query(models.User).filter(models.User.email == test_user['email']).first()
    test_credit_analyst_user_id = db.query(models.User).filter(models.User.email == test_credit_analyst_user['email']).first()
    workflow_action = workflow_test_data
    assert workflow_action.workflow_stage == WorkflowStage.MAKER
    
    # Submit as maker
    maker_response = client.post(
        f"/submit_rating/{workflow_action.rating_instance_id}/{workflow_action.id}",
        cookies={"Authorization": maker_auth_cookie},
        allow_redirects=False
    )
    assert maker_response.status_code == 303
    
    # Get checker action step
    checker_action_step = (db.query(WorkflowAction)
        .filter(WorkflowAction.workflow_cycle_id == workflow_action.workflow_cycle_id)
        .filter(WorkflowAction.workflow_stage == WorkflowStage.CHECKER)
        .first())
    
    # Submit as checker
    checker_auth_cookie = test_login(client, test_credit_analyst_user)
    checker_response = client.post(
        f"/submit_rating/{checker_action_step.rating_instance_id}/{checker_action_step.id}",
        cookies={"Authorization": checker_auth_cookie},
        allow_redirects=False
    )
    assert checker_response.status_code == 303
    
    # Get all user IDs first
    maker_id = db.query(models.User.id).filter(models.User.email == test_user['email']).scalar()
    checker_id = db.query(models.User.id).filter(models.User.email == test_credit_analyst_user['email']).scalar()
    approver1_id = db.query(models.User.id).filter(models.User.email == test_approver_1_user['email']).scalar()
    approver2_id = db.query(models.User.id).filter(models.User.email == test_approver_2_user['email']).scalar()
    approver3_id = db.query(models.User.id).filter(models.User.email == test_approver_3_user['email']).scalar()

    # Initial Maker and Checker steps remain the same...
    # [Your existing maker and checker approval code here]

    # Get the approver stage workflow action
    approver_action = (db.query(WorkflowAction)
        .filter(WorkflowAction.workflow_cycle_id == workflow_action.workflow_cycle_id)
        .filter(WorkflowAction.workflow_stage == WorkflowStage.APPROVER)
        .filter(WorkflowAction.head == True)
        .first())
    
    # First approver submission
    approver1_auth_cookie = test_login(client, test_approver_1_user)
    approver1_response = client.post(
        f"/submit_rating/{approver_action.rating_instance_id}/{approver_action.id}",
        cookies={"Authorization": approver1_auth_cookie},
        allow_redirects=False
    )
    assert approver1_response.status_code == 303

    # Second approver submission
    approver2_auth_cookie = test_login(client, test_approver_2_user)
    
    latest_wf_id= WorkflowAction.get_active_workflow(db=db,work_flow_cycle_id= workflow_action.workflow_cycle_id).id

    approver2_response = client.post(
        f"/submit_rating/{approver_action.rating_instance_id}/{latest_wf_id}",
        cookies={"Authorization": approver2_auth_cookie},
        allow_redirects=False
    )
    assert approver2_response.status_code == 303

    # Third approver submission
    approver3_auth_cookie = test_login(client, test_approver_3_user)

    latest_wf_id= WorkflowAction.get_active_workflow(db=db,work_flow_cycle_id= workflow_action.workflow_cycle_id).id
    approver3_response = client.post(
        f"/submit_rating/{approver_action.rating_instance_id}/{latest_wf_id}",
        cookies={"Authorization": approver3_auth_cookie},
        allow_redirects=False
    )
    assert approver3_response.status_code == 303


    # Check each step in the sequence

    # All steps including approver stages should be present
    expected_steps = [
        # Initial maker step
        {"stage": WorkflowStage.MAKER, "action_type": ActionRight.INIT, "user_id": test_user_id.id},
        # Maker approval
        {"stage": WorkflowStage.MAKER, "action_type": ActionRight.APPROVE, "user_id": test_user_id.id},
        # Exit maker stage
        {"stage": WorkflowStage.MAKER, "action_type": ActionRight.EXIT, "user_id": None},
        # Init checker stage
        {"stage": WorkflowStage.CHECKER, "action_type": ActionRight.INIT, "user_id": None},
        # Checker approval
        {"stage": WorkflowStage.CHECKER, "action_type": ActionRight.APPROVE, "user_id": test_credit_analyst_user_id.id},
        # Exit checker stage
        {"stage": WorkflowStage.CHECKER, "action_type": ActionRight.EXIT, "user_id": None},
        
        # Init approver stage
        {"stage": WorkflowStage.APPROVER, "action_type": ActionRight.INIT, "user_id": None},

        # {"stage": WorkflowStage.MAKER, "action_type": ActionRight.APPROVE, "user_id": maker_id},
        # {"stage": WorkflowStage.MAKER, "action_type": ActionRight.EXIT, "user_id": None},
        # {"stage": WorkflowStage.CHECKER, "action_type": ActionRight.INIT, "user_id": None},
        # {"stage": WorkflowStage.CHECKER, "action_type": ActionRight.APPROVE, "user_id": checker_id},
        # {"stage": WorkflowStage.CHECKER, "action_type": ActionRight.EXIT, "user_id": None},
        # {"stage": WorkflowStage.APPROVER, "action_type": ActionRight.INIT, "user_id": None},
        # Approver steps
        {"stage": WorkflowStage.APPROVER, "action_type": ActionRight.APPROVE, "user_id": approver1_id},
        {"stage": WorkflowStage.APPROVER, "action_type": ActionRight.APPROVE, "user_id": approver2_id},
        {"stage": WorkflowStage.APPROVER, "action_type": ActionRight.APPROVE, "user_id": approver3_id},
        {"stage": WorkflowStage.APPROVER, "action_type": ActionRight.EXIT, "user_id": None},
        {"stage": WorkflowStage.APPROVED, "action_type": ActionRight.INIT, "user_id": None}
    ]


    # Initial workflow stage check
    assert workflow_action.workflow_stage == WorkflowStage.MAKER, f"Initial workflow stage should be MAKER, got {workflow_action.workflow_stage}"

    # Response status code checks
    assert maker_response.status_code == 303, f"Maker submission should return 303 redirect, got {maker_response.status_code}"
    assert checker_response.status_code == 303, f"Checker submission should return 303 redirect, got {checker_response.status_code}"
    assert approver1_response.status_code == 303, f"First approver submission should return 303 redirect, got {approver1_response.status_code}"
    assert approver2_response.status_code == 303, f"Second approver submission should return 303 redirect, got {approver2_response.status_code}"
    assert approver3_response.status_code == 303, f"Third approver submission should return 303 redirect, got {approver3_response.status_code}"
    db.expire_all()
    # Get final workflow actions
    final_workflow_actions = (
        db.query(WorkflowAction)
        .filter(WorkflowAction.workflow_cycle_id == workflow_action.workflow_cycle_id)
        .order_by(WorkflowAction.action_count_customer_level)
        .all()
    )
    # Workflow action checks
    for i, expected in enumerate(expected_steps):
        action = final_workflow_actions[i]
        assert action.workflow_stage == expected["stage"], \
            f"Step {i+1}: Expected workflow stage {expected['stage']}, got {action.workflow_stage}"
        assert action.action_type == expected["action_type"], \
            f"Step {i+1}: Expected action type {expected['action_type']}, got {action.action_type}"
        assert action.user_id == expected["user_id"], \
            f"Step {i+1}: Expected user ID {expected['user_id']}, got {action.user_id}"

        # Head and stale flag checks
        if i == len(expected_steps) - 1:
            assert action.head == True, \
                f"Step {i+1} (final step): Should be head=True, got head=False"
        else:
            assert action.head == False, \
                f"Step {i+1}: Should be head=False, got head=True, for action id: {str(action.id)} which has {action.head}" 


        # Action count check
        assert action.action_count_customer_level == i + 1, \
            f"Step {i+1}: Expected action count {i+1}, got {action.action_count_customer_level}"

    final_workflow=final_workflow_actions[-1] # the last workflow
    # Final workflow stage check
    assert final_workflow.workflow_stage == WorkflowStage.APPROVED, \
        f"Final workflow stage should be APPROVED, got {final_workflow.workflow_stage}"



def test_checker_edit_workflow(
    client,
    db,
    test_user,
    test_credit_analyst_user,
    workflow_test_data
):
    """
    Test workflow when checker makes an edit:
    1. Maker approves initially
    2. Checker makes an edit (stays in checker stage)
    3. Checker approves the edit
    4. Goes back to maker for approval
    5. Maker approves
    6. Goes to approver stage
    """
    # Initial maker approval
    maker_auth_cookie = test_login(client, test_user)
    workflow_action = workflow_test_data
    assert workflow_action.workflow_stage == WorkflowStage.MAKER, "Should start at MAKER stage"
    
    # Submit as maker
    maker_response = client.post(
        f"/submit_rating/{workflow_action.rating_instance_id}/{workflow_action.id}",
        cookies={"Authorization": maker_auth_cookie},
        allow_redirects=False
    )
    assert maker_response.status_code == 303
    
    # Get checker action and verify stage
    db.expire_all()
    checker_action = (
        db.query(WorkflowAction)
        .filter(WorkflowAction.workflow_cycle_id == workflow_action.workflow_cycle_id)
        .filter(WorkflowAction.workflow_stage == WorkflowStage.CHECKER)
        .filter(WorkflowAction.head == True)
        .first()
    )
    assert checker_action is not None, "Should have progressed to CHECKER stage"
    
    # Checker makes an edit
    checker_auth_cookie = test_login(client, test_credit_analyst_user)
    edit_response = client.post(
        f"/edit_rating/{checker_action.rating_instance_id}/{checker_action.id}",
        cookies={"Authorization": checker_auth_cookie},
        allow_redirects=False
    )
    assert edit_response.status_code == 303
    
    # Verify still in CHECKER stage after edit
    db.expire_all()
    checker_after_edit = (
        db.query(WorkflowAction)
        .filter(WorkflowAction.workflow_cycle_id == workflow_action.workflow_cycle_id)
        .filter(WorkflowAction.head == True)
        .first()
    )
    assert checker_after_edit.workflow_stage == WorkflowStage.CHECKER, "Should remain in CHECKER stage after edit"
    assert checker_after_edit.action_type == ActionRight.EDIT, "Should have EDIT action type"
    
    # Checker approves their edit
    checker_approve_response = client.post(
        f"/submit_rating/{checker_after_edit.rating_instance_id}/{checker_after_edit.id}",
        cookies={"Authorization": checker_auth_cookie},
        allow_redirects=False
    )
    assert checker_approve_response.status_code == 303
    
    # Verify it went back to MAKER stage after checker approved their edit
    db.expire_all()
    maker_action_after_edit = (
        db.query(WorkflowAction)
        .filter(WorkflowAction.workflow_cycle_id == workflow_action.workflow_cycle_id)
        .filter(WorkflowAction.head == True)
        .first()
    )
    assert maker_action_after_edit.workflow_stage == WorkflowStage.MAKER, \
        "Should return to MAKER stage after checker approves their edit"
    
    # Maker approves the edited version
    maker_approve_edit_response = client.post(
        f"/submit_rating/{maker_action_after_edit.rating_instance_id}/{maker_action_after_edit.id}",
        cookies={"Authorization": maker_auth_cookie},
        allow_redirects=False
    )
    assert maker_approve_edit_response.status_code == 303
    
    # Verify progression to APPROVER stage
    db.expire_all()
    final_action = (
        db.query(WorkflowAction)
        .filter(WorkflowAction.workflow_cycle_id == workflow_action.workflow_cycle_id)
        .filter(WorkflowAction.head == True)
        .first()
    )
    assert final_action.workflow_stage == WorkflowStage.APPROVER, "Should progress to APPROVER stage"
    
    # Verify the complete sequence of actions
    all_actions = (
        db.query(WorkflowAction)
        .filter(WorkflowAction.workflow_cycle_id == workflow_action.workflow_cycle_id)
        .order_by(WorkflowAction.action_count_customer_level)
        .all()
    )
    
    expected_sequence = [
        (WorkflowStage.MAKER, ActionRight.INIT),
        (WorkflowStage.MAKER, ActionRight.APPROVE),
        (WorkflowStage.MAKER, ActionRight.EXIT),
        (WorkflowStage.CHECKER, ActionRight.INIT),
        (WorkflowStage.CHECKER, ActionRight.EDIT),     # Checker's edit
        (WorkflowStage.CHECKER, ActionRight.APPROVE),  # Checker approves their edit
        (WorkflowStage.CHECKER, ActionRight.EXIT),
        (WorkflowStage.MAKER, ActionRight.INIT),       # Back to maker for edit approval
        (WorkflowStage.MAKER, ActionRight.APPROVE),    # Maker approves edit
        (WorkflowStage.MAKER, ActionRight.EXIT),
        (WorkflowStage.APPROVER, ActionRight.INIT),    # Finally to approver
    ]
    
    for i, (expected_stage, expected_action) in enumerate(expected_sequence):
        action = all_actions[i]
        assert action.workflow_stage == expected_stage, \
            f"Step {i+1}: Expected stage {expected_stage}, got {action.workflow_stage}"
        assert action.action_type == expected_action, \
            f"Step {i+1}: Expected action {expected_action}, got {action.action_type}"
        
        # Verify head and stale flags
        if i == len(expected_sequence) - 1:
            assert action.head == True, f"Final action should be head"
            assert action.is_stale == False, f"Final action should not be stale"
        else:
            assert action.head == False, f"Non-final action should not be head"
            assert action.is_stale == True, f"Non-final action should be stale"


def test_approver_edit_workflow(
    client,
    db,
    test_user,
    test_credit_analyst_user,
    test_approver_1_user,
    workflow_test_data
):
    """
    Test workflow when approver makes an edit:
    1. Maker approves initially
    2. Checker approves
    3. Approver makes an edit (stays in approver stage)
    4. Approver approves their edit
    5. Goes back to maker for approval
    6. Maker approves
    7. Goes back to checker
    8. Checker approves
    9. Returns to approver stage
    """
    # Initial maker approval
    maker_auth_cookie = test_login(client, test_user)
    workflow_action = workflow_test_data
    
    # Submit as maker
    maker_response = client.post(
        f"/submit_rating/{workflow_action.rating_instance_id}/{workflow_action.id}",
        cookies={"Authorization": maker_auth_cookie},
        allow_redirects=False
    )
    assert maker_response.status_code == 303
    
    # Submit as checker
    checker_auth_cookie = test_login(client, test_credit_analyst_user)
    checker_action = WorkflowAction.get_active_workflow(db, workflow_action.workflow_cycle_id)
    checker_response = client.post(
        f"/submit_rating/{checker_action.rating_instance_id}/{checker_action.id}",
        cookies={"Authorization": checker_auth_cookie},
        allow_redirects=False
    )
    assert checker_response.status_code == 303
    
    # Approver makes an edit
    approver_auth_cookie = test_login(client, test_approver_1_user)
    approver_action = WorkflowAction.get_active_workflow(db, workflow_action.workflow_cycle_id)
    edit_response = client.post(
        f"/edit_rating/{approver_action.rating_instance_id}/{approver_action.id}",
        cookies={"Authorization": approver_auth_cookie},
        allow_redirects=False
    )
    assert edit_response.status_code == 303
    
    # Verify still in APPROVER stage after edit
    db.expire_all()
    approver_after_edit = WorkflowAction.get_active_workflow(db, workflow_action.workflow_cycle_id)
    assert approver_after_edit.workflow_stage == WorkflowStage.APPROVER
    assert approver_after_edit.action_type == ActionRight.EDIT
    
    # Approver approves their edit
    approver_approve_response = client.post(
        f"/submit_rating/{approver_after_edit.rating_instance_id}/{approver_after_edit.id}",
        cookies={"Authorization": approver_auth_cookie},
        allow_redirects=False
    )
    assert approver_approve_response.status_code == 303
    
    # Verify it went back to MAKER stage
    db.expire_all()
    maker_action_after_edit = WorkflowAction.get_active_workflow(db, workflow_action.workflow_cycle_id)
    assert maker_action_after_edit.workflow_stage == WorkflowStage.MAKER
    
    # Maker approves the edited version
    maker_approve_edit_response = client.post(
        f"/submit_rating/{maker_action_after_edit.rating_instance_id}/{maker_action_after_edit.id}",
        cookies={"Authorization": maker_auth_cookie},
        allow_redirects=False
    )
    assert maker_approve_edit_response.status_code == 303
    
    # Checker approves the edited version
    db.expire_all()
    checker_action_after_edit = WorkflowAction.get_active_workflow(db, workflow_action.workflow_cycle_id)
    checker_approve_edit_response = client.post(
        f"/submit_rating/{checker_action_after_edit.rating_instance_id}/{checker_action_after_edit.id}",
        cookies={"Authorization": checker_auth_cookie},
        allow_redirects=False
    )
    assert checker_approve_edit_response.status_code == 303
    
    # Verify final progression back to APPROVER stage
    db.expire_all()
    final_action = WorkflowAction.get_active_workflow(db, workflow_action.workflow_cycle_id)
    assert final_action.workflow_stage == WorkflowStage.APPROVER
    
    # Verify the complete sequence of actions
    all_actions = (
        db.query(WorkflowAction)
        .filter(WorkflowAction.workflow_cycle_id == workflow_action.workflow_cycle_id)
        .order_by(WorkflowAction.action_count_customer_level)
        .all()
    )
    
    expected_sequence = [
        (WorkflowStage.MAKER, ActionRight.INIT),
        (WorkflowStage.MAKER, ActionRight.APPROVE),
        (WorkflowStage.MAKER, ActionRight.EXIT),
        (WorkflowStage.CHECKER, ActionRight.INIT),
        (WorkflowStage.CHECKER, ActionRight.APPROVE),
        (WorkflowStage.CHECKER, ActionRight.EXIT),
        (WorkflowStage.APPROVER, ActionRight.INIT),
        (WorkflowStage.APPROVER, ActionRight.EDIT),      # Approver's edit
        (WorkflowStage.APPROVER, ActionRight.APPROVE),   # Approver approves their edit
        (WorkflowStage.APPROVER, ActionRight.EXIT),
        (WorkflowStage.MAKER, ActionRight.INIT),         # Back to maker
        (WorkflowStage.MAKER, ActionRight.APPROVE),      # Maker approves edit
        (WorkflowStage.MAKER, ActionRight.EXIT),
        (WorkflowStage.CHECKER, ActionRight.INIT),       # To checker
        (WorkflowStage.CHECKER, ActionRight.APPROVE),    # Checker approves
        (WorkflowStage.CHECKER, ActionRight.EXIT),
        (WorkflowStage.APPROVER, ActionRight.INIT),      # Back to approver
    ]
    
    for i, (expected_stage, expected_action) in enumerate(expected_sequence):
        action = all_actions[i]
        assert action.workflow_stage == expected_stage, \
            f"Step {i+1}: Expected stage {expected_stage}, got {action.workflow_stage}"
        assert action.action_type == expected_action, \
            f"Step {i+1}: Expected action {expected_action}, got {action.action_type}"
        
        if i == len(expected_sequence) - 1:
            assert action.head == True
            assert action.is_stale == False
        else:
            assert action.head == False
            assert action.is_stale == True




def test_unauthorized_edit_attempts(
    client,
    db,
    test_user,
    test_credit_analyst_user,
    test_approver_1_user,
    workflow_test_data
):
    """Test unauthorized edit attempts at different workflow stages"""
    
    # Setup: Get workflow to checker stage
    maker_auth_cookie = test_login(client, test_user)
    workflow_action = workflow_test_data
    
    # Submit as maker to move to checker stage
    maker_response = client.post(
        f"/submit_rating/{workflow_action.rating_instance_id}/{workflow_action.id}",
        cookies={"Authorization": maker_auth_cookie},
        allow_redirects=False
    )
    assert maker_response.status_code == 303
    
    # Test 1: Maker trying to edit in checker stage (unauthorized)
    checker_action = WorkflowAction.get_active_workflow(db, workflow_action.workflow_cycle_id)
    edit_response = client.post(
        f"/edit_rating/{checker_action.rating_instance_id}/{checker_action.id}",
        cookies={"Authorization": maker_auth_cookie},
        allow_redirects=False
    )
    error = WorkflowError.model_validate(edit_response.json())
    assert error.code == WorkflowErrorCode.UNAUTHORIZED_ROLE
    
    # Test 2: Random approver trying to edit in checker stage
    approver_auth_cookie = test_login(client, test_approver_1_user)
    edit_response = client.post(
        f"/edit_rating/{checker_action.rating_instance_id}/{checker_action.id}",
        cookies={"Authorization": approver_auth_cookie},
        allow_redirects=False
    )
    error = WorkflowError.model_validate(edit_response.json())
    assert error.code == WorkflowErrorCode.UNAUTHORIZED_ROLE

    # Move to approver stage
    checker_auth_cookie = test_login(client, test_credit_analyst_user)
    checker_response = client.post(
        f"/submit_rating/{checker_action.rating_instance_id}/{checker_action.id}",
        cookies={"Authorization": checker_auth_cookie},
        allow_redirects=False
    )
    
    # Test 3: Checker trying to edit in approver stage
    approver_action = WorkflowAction.get_active_workflow(db, workflow_action.workflow_cycle_id)
    edit_response = client.post(
        f"/edit_rating/{approver_action.rating_instance_id}/{approver_action.id}",
        cookies={"Authorization": checker_auth_cookie},
        allow_redirects=False
    )
    error = WorkflowError.model_validate(edit_response.json())
    assert error.code == WorkflowErrorCode.UNAUTHORIZED_ROLE
