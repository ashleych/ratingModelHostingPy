import os
import csv
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.models import Base, BusinessUnit, MasterRatingScale, Customer, FinancialsPeriod,LineItemMeta, Template, TemplateSourceCSV, WorkflowAction
from enum import Enum

DB_NAME = "rating_model_py_app"
# sudo postgres -d rating_model_py_app
PROJECT_DIR= os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIRECTORY = os.path.join(PROJECT_DIR,"Template-Basic")
TEMPLATE_START_YEAR = 2020
TEMPLATE_END_YEAR = 2025

class WorkflowActionType(Enum):
    DRAFT = "draft"

class FinStatementType(Enum):
    PNL = "pnl"
    BS = "bs"
    CF='cashflow'
    ALL='all'
    
    @classmethod
    def _missing_(cls, value):
        return cls.ALL

def create_engine_and_session(db_path):
    SQLALCHEMY_DATABASE_URL =f"postgresql://postgres:postgres@localhost/{db_path}"

    engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine,autocommit=False, autoflush=False)
    return engine, Session()

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
        tables = [
'businessunit',
'customer',
'financialsperiod',
'financialstatement',
'lineitemmeta',
'lineitemvalue',
'masterratingscale',
'ratingfactor',
'ratingfactorattribute',
'ratingfactorscore',
'ratinginstance',
'ratingmodel',
'template',
'templatesourcecsv',
'workflowaction',
            # Add any other tables that might be in your schema
        ]
    
        with engine.begin() as conn:
            # Disable triggers temporarily
            conn.execute(text("SET session_replication_role = 'replica';"))
            
            for table_name in tables:
                # Use DROP CASCADE for each table
                conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
            
            # Re-enable triggers
            conn.execute(text("SET session_replication_role = 'origin';"))

# Use this function instead of Base.metadata.drop_all(engine)
    drop_tables_in_order(engine)
    # Drop all tables
    Base.metadata.drop_all(engine)
    # Create all tables
    Base.metadata.create_all(engine)
         
    session.commit()
    insert_quarter_end_dates(session, TEMPLATE_START_YEAR, TEMPLATE_END_YEAR)
    business_units_data=["Large Corporate", "Mid Corporate", "SME", "Financial Institution", "Private Banking", "Structured Finance"]
    # for name in business_units_data:
    #         business_unit = BusinessUnit(name=name)
    #         session.add(business_unit)
    # session.commit()
    business_units = {}
    for name in business_units_data:
        business_unit = BusinessUnit(name=name)
        session.add(business_unit)
        session.flush()  # This will assign an id to the business_unit
        business_units[name] = business_unit
    
    session.commit()   
        # Add master rating scale data

    mrs_data=[MasterRatingScale(rating_grade= "1", pd= 0.000050), MasterRatingScale(rating_grade= "2+", pd= 0.000070), MasterRatingScale(rating_grade= "2", pd= 0.000120), MasterRatingScale(rating_grade= "2-", pd= 0.000190), MasterRatingScale(rating_grade= "3+", pd= 0.000300), MasterRatingScale(rating_grade= "3", pd= 0.000490), MasterRatingScale(rating_grade= "3-", pd= 0.000790), MasterRatingScale(rating_grade= "4+", pd= 0.001270), MasterRatingScale(rating_grade= "4", pd= 0.002050), MasterRatingScale(rating_grade= "4-", pd= 0.003300), MasterRatingScale(rating_grade= "5+", pd= 0.005310), MasterRatingScale(rating_grade= "5", pd= 0.008550), MasterRatingScale(rating_grade= "5-", pd= 0.013760), MasterRatingScale(rating_grade= "6+", pd= 0.022150), MasterRatingScale(rating_grade= "6", pd= 0.035670), MasterRatingScale(rating_grade= "6-", pd= 0.057420), MasterRatingScale(rating_grade= "7+", pd= 0.092440), MasterRatingScale(rating_grade= "7", pd= 0.148820), MasterRatingScale(rating_grade= "7-", pd= 0.239590), MasterRatingScale(rating_grade= "8", pd= 1.000000), MasterRatingScale(rating_grade= "9", pd= 1.000000), MasterRatingScale(rating_grade= "10", pd= 1.000000)]
    session.add_all(mrs_data)
        # Add customers
    customers = [
    Customer(
        customer_name="ABC Corporation",
        cif_number="CIF-123456",
        group_name="ABC Group",
        business_unit_id=business_units["Large Corporate"].id,
        relationship_type="Prospect",
        internal_risk_rating="2",
        workflow_action_type=WorkflowActionType.DRAFT.value
    ),
    Customer(
        customer_name="XYZ Enterprises",
        cif_number="CIF-789012",
        group_name="XYZ Group",
        business_unit_id=business_units["Mid Corporate"].id,
        relationship_type="Existing",
        internal_risk_rating="2",
        workflow_action_type=WorkflowActionType.DRAFT.value
    ),
    Customer(
        customer_name="DEF Ltd",
        cif_number="1001",
        group_name="ABC Group",
        business_unit_id=business_units["Large Corporate"].id,
        relationship_type="Prospect",
        internal_risk_rating="5",
        workflow_action_type=WorkflowActionType.DRAFT.value
    ),
    Customer(
        customer_name="PQR Inc",
        cif_number="1002",
        group_name="XYZ Group",
        business_unit_id=business_units["Large Corporate"].id,
        relationship_type="Existing",
        internal_risk_rating="5+",
        workflow_action_type=WorkflowActionType.DRAFT.value
    ),
    Customer(
        customer_name="GHI Corporation",
        cif_number="1003",
        group_name="DEF Group",
        business_unit_id=business_units["Large Corporate"].id,
        relationship_type="Prospect",
        internal_risk_rating="2-",
        workflow_action_type=WorkflowActionType.DRAFT.value
    ),
    Customer(
        customer_name="LMN Enterprises",
        cif_number="1004",
        group_name="PQR Group",
        business_unit_id=business_units["Large Corporate"].id,
        relationship_type="Existing",
        internal_risk_rating="2",
        workflow_action_type=WorkflowActionType.DRAFT.value
    ),
    Customer(
        customer_name="JKL Ltd",
        cif_number="1005",
        group_name="LMN Group",
        business_unit_id=business_units["Large Corporate"].id,
        relationship_type="Prospect",
        internal_risk_rating="2",
        workflow_action_type=WorkflowActionType.DRAFT.value
    )
]

    # After defining the customers list
    for customer in customers:
        workflow_action = create_update_workflow_action(session, customer.cif_number, WorkflowActionType.DRAFT)
        customer.workflow_action = workflow_action
        session.add(customer)

    session.commit()
    # for customer in customers:
    #     workflow_action = create_update_workflow_action(session, customer.cif_number, WorkflowActionType.DRAFT)
    #     customer.workflow_action = workflow_action
    #     customer.workflow_action_type = WorkflowActionType.DRAFT.value
    #     session.add(customer)
    #     session.commit()
        

    template = create_template(session, "FinTemplate", "fin_template.csv")
        
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

def create_update_workflow_action(session, cif_number, status):
    max_action = session.query(WorkflowAction).filter_by(customer_id=cif_number).order_by(WorkflowAction.id.desc()).first()
    
    new_action = WorkflowAction(
        customer_id=cif_number,
        action_count_customer_level=max_action.action_count_customer_level + 1 if max_action else 1,
        action_by="Maker",
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

if __name__ == "__main__":
    init_db(DB_NAME)