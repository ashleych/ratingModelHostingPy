from email import policy
import os
import csv
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi.encoders import jsonable_encoder
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.rating_model_model import MasterRatingScale, TemplateSourceCSV
from models.statement_models import Template
from models.statement_models import FinancialsPeriod, LineItemMeta
from models.models import Base, BusinessUnit, Customer, Role, User
from enum import Enum

from enums_and_constants import ActionRight, WorkflowStage,RejectionFlow
from typing import Dict,Any,List
from models.policy_rules_model import PolicyRule, RatingAccessRule
from sqlalchemy.orm import Session

from models.workflow_model import WorkflowAction
from schema.schema import User as UserSchema
from security import get_hashed_password

DB_NAME = "rating_model_py_app"
# sudo postgres -d rating_model_py_app
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIRECTORY = os.path.join(PROJECT_DIR, "Template-Basic")
TEMPLATE_START_YEAR = 2020
TEMPLATE_END_YEAR = 2025


# class WorkflowActionType(Enum):
#     DRAFT = "draft"


class FinStatementType(Enum):
    PNL = "pnl"
    BS = "bs"
    CF = 'cashflow'
    ALL = 'all'

    @classmethod
    def _missing_(cls, value):
        return cls.ALL


def create_engine_and_session(db_path):
    SQLALCHEMY_DATABASE_URL = f"postgresql://postgres:postgres@localhost/{db_path}"

    engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return engine, Session()

from sqlalchemy.orm import Session
from enum import Enum
from typing import Dict, Any


def init_policy(session: Session, business_units: Dict[str, Any]) -> None:
    default_policies = {
        "Large Corporate": {
            "name": "Large Corporate Credit Approval Policy",
            "description": "Standard workflow for large corporate credit approval process",
            "access_rules": [
                # Maker stage rules
                {
                    "role_name": "Credit Analyst",
                    "workflow_stage": WorkflowStage.MAKER,
                    "action_rights": [
                        ActionRight.VIEW,
                        ActionRight.CREATE,
                        ActionRight.EDIT,
                        ActionRight.SUBMIT
                    ],
                    "is_mandatory": True,
                    "rejection_flow": RejectionFlow.TO_MAKER
                },
                {
                    "role_name": "Relationship Manager",
                    "workflow_stage": WorkflowStage.MAKER,
                    "action_rights": [
                        ActionRight.VIEW,
                        ActionRight.CREATE,
                        ActionRight.EDIT,
                        ActionRight.SUBMIT
                    ]
                },
                {
                    "role_name": "Relationship Manager",
                    "workflow_stage": WorkflowStage.CHECKER,
                    "action_rights": [
                        ActionRight.VIEW
                    ]
                },
                {
                    "role_name": "Relationship Manager",
                    "workflow_stage": WorkflowStage.APPROVER,
                    "action_rights": [
                        ActionRight.VIEW
                    ]
                },
                {
                    "role_name": "Relationship Manager",
                    "workflow_stage": WorkflowStage.APPROVED,
                    "action_rights": [
                        ActionRight.VIEW
                    ]
                },
                {
                    "role_name": "Credit Analyst",
                    "workflow_stage": WorkflowStage.CHECKER,
                    "action_rights": [
                        ActionRight.VIEW,
                        ActionRight.EDIT,
                        ActionRight.SUBMIT

                    ]
                },
                {
                    "role_name": "Credit Analyst",
                    "workflow_stage": WorkflowStage.APPROVER,
                    "action_rights": [
                        ActionRight.VIEW
                    ]
                },
                {
                    "role_name": "Credit Analyst",
                    "workflow_stage": WorkflowStage.APPROVED,
                    "action_rights": [
                        ActionRight.VIEW
                    ]
                },
                # Checker stage rules
                {
                    "role_name": "BU Head",
                    "workflow_stage": WorkflowStage.CHECKER,
                    "action_rights": [
                        ActionRight.VIEW,
                        ActionRight.EDIT,
                        ActionRight.SUBMIT,
                        ActionRight.COMMENT
                    ],
                    "is_mandatory": True,
                    "rejection_flow": RejectionFlow.TO_MAKER
                },
                # Approver stage rules
                {
                    "role_name": "CRO",
                    "workflow_stage": WorkflowStage.APPROVER,
                    "action_rights": [
                        ActionRight.VIEW,
                        ActionRight.EDIT,
                        ActionRight.SUBMIT,
                        ActionRight.DELETE,
                        ActionRight.COMMENT
                    ],
                    "approval_order": 1,
                    "is_mandatory": True,
                    "rejection_flow": RejectionFlow.TO_MAKER
                }
            ]
        }
    }

    for bu_name, policy_config in default_policies.items():
        if bu_name in business_units:
            policy = PolicyRule(
                name=policy_config["name"],
                business_unit_id=business_units[bu_name].id,
                description=policy_config["description"],
                is_active=True
            )
            session.add(policy)
            session.flush()

            for rule_config in policy_config["access_rules"]:
                access_rule = RatingAccessRule(
                    policy_id=policy.id,
                    **rule_config
                )
                session.add(access_rule)

    session.commit()

# def init_policy(session: Session, business_units: Dict[str, Any]) -> None:
#     """
#     Initialize policy rules for each business unit.
    
#     Args:
#         session: SQLAlchemy session
#         business_units: Dictionary of business units with their IDs
#     """
#     # First, get all role IDs
#     roles = {
#         role.name: role.id 
#         for role in session.query(Role).filter(Role.name.in_([
#             "Credit Analyst", "Relationship Manager", "BU Head", 
#             "Country Head", "CRO", "CEO"
#         ])).all()
#     }
    
#     # Define the base policy template
#     default_policies = {
#         "Large Corporate": {
#             "name": "Large Corporate Credit Approval Policy",
#             "description": "Standard workflow for large corporate credit approval process",
#             "stages": [
#                 {
#                     "stage": WorkflowStage.MAKER,
#                     "roles": [roles["Credit Analyst"], roles["Relationship Manager"]],
#                     "rights": ["CREATE", "EDIT","SUBMIT"],
#                     "min_count": 1
#                 },
#                 {
#                     "stage": WorkflowStage.CHECKER,
#                     "roles": [roles["BU Head"], roles["Country Head"]],
#                     "rights": ["CREATE", "EDIT","SUBMIT"],
#                     "min_count": 2
#                 },
#                 {
#                     "stage": WorkflowStage.APPROVER,
#                     "roles": [roles["CRO"], roles["CEO"]],
#                     "rights": ["CREATE", "EDIT", "DELETE","SUBMIT"],
#                     "min_count": 1,
#                     "sequential_approval": True,
#                     "rejection_flow": RejectionFlow.TO_MAKER
#                 }
#             ]
#         },
#         "Mid Corporate": {
#             "name": "Mid Corporate Credit Approval Policy",
#             "description": "Standard workflow for mid corporate credit approval process",
#             "stages": [
#                 {
#                     "stage": WorkflowStage.MAKER,
#                     "roles": [roles["Credit Analyst"], roles["Relationship Manager"]],
#                     "rights": ["CREATE", "EDIT","SUBMIT"],
#                     "min_count": 1
#                 },
#                 {
#                     "stage": WorkflowStage.CHECKER,
#                     "roles": [roles["BU Head"]],
#                     "rights": ["CREATE", "EDIT","SUBMIT"],
#                     "min_count": 1
#                 },
#                 {
#                     "stage": WorkflowStage.APPROVER,
#                     "roles": [roles["CRO"]],
#                     "rights": ["CREATE", "EDIT", "DELETE","SUBMIT"],
#                     "min_count": 1,
#                     "sequential_approval": True,
#                     "rejection_flow": RejectionFlow.TO_MAKER
#                 }
#             ]
#         }
#     }

#     # Create policy rules for each business unit
#     for bu_name, policy_config in default_policies.items():
#         if bu_name in business_units:
#             # Create main policy rule
#             policy_rule = PolicyRule(
#                 name=policy_config["name"],
#                 business_unit_id=business_units[bu_name].id,
#                 description=policy_config["description"],
#                 is_active=True
#             )
#             session.add(policy_rule)
#             session.flush()  # Get the policy ID

#             # Create workflow stages
#             for stage_config in policy_config["stages"]:
#                 workflow_stage = WorkflowStageConfig(
#                     policy_id=policy_rule.id,
#                     stage=stage_config["stage"],
#                     allowed_roles=jsonable_encoder(stage_config["roles"]),  # Now contains role IDs instead of names
#                     rights=stage_config["rights"],
#                     min_count=stage_config["min_count"]
#                 )

#                 # Add approver-specific configurations
#                 if stage_config["stage"] == WorkflowStage.APPROVER:
#                     workflow_stage.is_sequential = stage_config["sequential_approval"]
#                     workflow_stage.rejection_flow = stage_config["rejection_flow"]

#                 session.add(workflow_stage)

#     session.commit()

def init_db(db_path):
    engine, session = create_engine_and_session(db_path)

    from sqlalchemy import text
#     def drop_all_tables_without_fk_checks(engine):
#         with engine.begin() as conn:
#             conn.execute(text("SET CONSTRAINTS ALL DEFERRED"))
#             Base.metadata.drop_all(conn)
#             conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

# # Use this function instead of Base.metadata.drop_all(engine)
#     drop_all_tables_without_fk_checks(engine)
    def drop_tables_in_order(engine):
        # Define the order to drop tables
        # Start with tables that have the most dependencies and work backwards
        tables = ['businessunit', 'users', 'role', 'customer', 'financialsperiod', 'financialstatement', 'lineitemmeta', 'lineitemvalue', 'masterratingscale', 'ratingfactor', 'ratingfactorattribute', 'ratingfactorscore','ratingmodelapplicabilityrules',
            'ratinginstance', 'ratingmodel', 'template', 'templatesourcecsv', 'workflowaction', 'workflow_step', 'ratinginstance_version', 'workflow_assignment','workflow_stage_config','policy_rule','rating_access_rules']  # Add any other tables that might be in your schema ]
        with engine.begin() as conn:
            # Disable triggers temporarily
            conn.execute(text("SET session_replication_role = 'replica';"))

            for table_name in tables:
                # Use DROP CASCADE for each table
                conn.execute(
                    text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))

            # Re-enable triggers
            conn.execute(text("SET session_replication_role = 'origin';"))

# Use this function instead of Base.metadata.drop_all(engine)
    drop_tables_in_order(engine)
    # Drop all tables
    Base.metadata.drop_all(engine)
    # Create all tables
    Base.metadata.create_all(engine)
    template = create_template(session, "FinTemplate", "fin_template.csv")

    session.commit()
    insert_quarter_end_dates(session, TEMPLATE_START_YEAR, TEMPLATE_END_YEAR)
    business_units_names = ["Large Corporate", "Mid Corporate", "SME",
        "Financial Institution", "Private Banking", "Structured Finance"]
    # for name in business_units_data:
    #         business_unit = BusinessUnit(name=name)
    #         session.add(business_unit)
    # session.commit()
    business_units = {}
    for name in business_units_names:
        business_unit = BusinessUnit(name=name, template_id=template.id)
        session.add(business_unit)
        session.flush()  # This will assign an id to the business_unit
        business_units[name] = business_unit

    session.commit()
        # Add master rating scale data

    mrs_data = [MasterRatingScale(rating_grade="1", pd=0.000050), MasterRatingScale(rating_grade="2+", pd=0.000070), MasterRatingScale(rating_grade="2", pd=0.000120), MasterRatingScale(rating_grade="2-", pd=0.000190), MasterRatingScale(rating_grade="3+", pd=0.000300), MasterRatingScale(rating_grade="3", pd=0.000490), MasterRatingScale(rating_grade="3-", pd=0.000790), MasterRatingScale(rating_grade="4+", pd=0.001270), MasterRatingScale(rating_grade="4", pd=0.002050), MasterRatingScale(rating_grade="4-", pd=0.003300), MasterRatingScale(rating_grade="5+", pd=0.005310),
                                  MasterRatingScale(rating_grade="5", pd=0.008550), MasterRatingScale(rating_grade="5-", pd=0.013760), MasterRatingScale(rating_grade="6+", pd=0.022150), MasterRatingScale(rating_grade="6", pd=0.035670), MasterRatingScale(rating_grade="6-", pd=0.057420), MasterRatingScale(rating_grade="7+", pd=0.092440), MasterRatingScale(rating_grade="7", pd=0.148820), MasterRatingScale(rating_grade="7-", pd=0.239590), MasterRatingScale(rating_grade="8", pd=1.000000), MasterRatingScale(rating_grade="9", pd=1.000000), MasterRatingScale(rating_grade="10", pd=1.000000)]
    session.add_all(mrs_data)
        # Add customers

    default_roles = [ { "name": "Credit Analyst", "description": "Analyzes credit applications and prepares credit assessments", "is_active": True }, { "name": "BU Head", "description": "Head of Business Unit, responsible for overseeing department operations", "is_active": True }, { "name": "CRO", "description": "Chief Risk Officer, oversees all aspects of risk management", "is_active": True }, { "name": "CEO", "description": "Chief Executive Officer, highest-ranking executive officer", "is_active": True }, { "name": "Country Head", "description": "Manages and oversees all operations within a country", "is_active": True }, { "name": "Relationship Manager", "description": "Manages client relationships and portfolio", "is_active": True } ]
   # Add each role if it doesn't exist
    for role_data in default_roles:
            # Check if role already exists
        existing_role = session.query(Role).filter(Role.name == role_data["name"]).first()
        
        if not existing_role:
            # Create new role with timestamp
            new_role = Role(
                name=role_data["name"],
                description=role_data["description"],
                is_active=role_data["is_active"],
            )
            session.add(new_role)
            print(f"Created role: {role_data['name']}")
        else:
            # Optionally update existing role's description and status
            existing_role.description = role_data["description"]
            existing_role.is_active = role_data["is_active"]
            print(f"Updated role: {role_data['name']}")

        session.commit()

    create_default_users(session=session)
    customers = [ Customer( customer_name="ABC Corporation", cif_number="CIF-123456", group_name="ABC Group", business_unit_id=business_units["Large Corporate"].id, relationship_type="Prospect", internal_risk_rating="2", ), Customer( customer_name="XYZ Enterprises", cif_number="CIF-789012", group_name="XYZ Group", business_unit_id=business_units["Mid Corporate"].id, relationship_type="Existing", internal_risk_rating="2", ), Customer( customer_name="DEF Ltd", cif_number="1001", group_name="ABC Group", business_unit_id=business_units["Large Corporate"].id, relationship_type="Prospect", internal_risk_rating="5", ), Customer( customer_name="PQR Inc", cif_number="1002", group_name="XYZ Group", business_unit_id=business_units["Large Corporate"].id, relationship_type="Existing", internal_risk_rating="5+", ), Customer( customer_name="GHI Corporation", cif_number="1003", group_name="DEF Group", business_unit_id=business_units["Large Corporate"].id, relationship_type="Prospect", internal_risk_rating="2-", ), Customer( customer_name="LMN Enterprises", cif_number="1004", group_name="PQR Group", business_unit_id=business_units["Large Corporate"].id, relationship_type="Existing", internal_risk_rating="2", ), Customer( customer_name="JKL Ltd", cif_number="1005", group_name="LMN Group", business_unit_id=business_units["Large Corporate"].id, relationship_type="Prospect", internal_risk_rating="2", ) ]
    init_policy(session,business_units=business_units) 
    # After defining the customers list
    for customer in customers:
        session.add(customer)

    session.commit()
    pnl_items = read_csv(os.path.join(TEMPLATE_DIRECTORY, template.template_source_csv.source_path))
    create_financial_template_line_items(session, pnl_items, template)
    
    session.commit()

def insert_quarter_end_dates(session, start_year, end_year):
    for year in range(start_year, end_year + 1):
        for quarter in range(1, 5):
            last_day_of_quarter = datetime(year, quarter * 3, 1) + timedelta(days=-1)
            fp = FinancialsPeriod(
                year=year,
                month=quarter * 3,
                date=last_day_of_quarter.day,
                type="quarter_end"
            )
            session.add(fp)

def create_update_workflow_action(session, cif_number, status,user):
    max_action = session.query(WorkflowAction).filter_by(customer_id=cif_number).order_by(WorkflowAction.id.desc()).first()
    
    new_action = WorkflowAction(
        customer_id=cif_number,
        action_count_customer_level=max_action.action_count_customer_level + 1 if max_action else 1,
        user_id=user.id,
        action_type=status.value,
        preceding_action_id=max_action.id if max_action else None,
        head=True
    )
    
    session.add(new_action)
    session.commit() 
    if max_action:
        max_action.succeeding_action_id = new_action.id
        max_action.head = False
    
    return new_action

def create_template(session, name, source_path):
    source = TemplateSourceCSV(source_path=os.path.join(TEMPLATE_DIRECTORY, source_path))
    session.add(source)
    template = Template(name=name, template_source_csv=source)
    session.add(template)
    session.commit()
    return template

def read_csv(file_path):
    with open(file_path, 'r') as file:
        return list(csv.reader(file))

def create_financial_template_line_items(session, records, template):
    for index, item in enumerate(records[1:], start=1):
        header = item[5] == "Yes"
        order_no = int(item[0].strip())
        display_order_no = int(item[1].strip()) if item[1].strip() else 0
        label = item[2].strip()
        name = item[4].strip()
        formula = item[5].strip()
        lag_months = int(item[7].strip()) if item[7].strip() else 0
        try:
            stmt_type = FinStatementType[item[3].strip().upper()].value
        except:
            stmt_type=FinStatementType.ALL.value
        
        if order_no != 0 and name:
            line_item = LineItemMeta(
                type="float",
                label=label,
                name=name,
                formula=formula,
                header=header,
                template_id=template.id,
                order_no=order_no,
                fin_statement_type=stmt_type,
                lag_months=lag_months,
                display_order_no=display_order_no
            )
            session.add(line_item)
            session.commit()




def create_default_users(session:Session) -> None:
    """
    Create default users with various role combinations using UserSchema
    """
    ## Get dict of role names and ids

    roles=session.query(Role).all()
    roles_dict = { r.name : r.id for r in roles }


    # Define default users with their roles
    default_users = [
        UserSchema(
            id=uuid4(),
            name="ashley",
            password=get_hashed_password('admin'),
            email="ashley.cherian@gmail.com",
            role=["Relationship Manager"],
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
    breakpoint()
    # Add the users to the database
    for user_schema in default_users:
        session.add(User(**user_schema.model_dump()))
        session.commit()


if __name__ == "__main__":
    init_db(DB_NAME)