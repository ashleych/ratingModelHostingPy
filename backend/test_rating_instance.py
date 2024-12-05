
from pathlib import Path
from fastapi.testclient import TestClient
from typing import List
import sys
from os import getenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker



# sys.path.insert(1, "/home/ashleyubuntu/ratingModelPython/backend")
from app import app
from config import DB_NAME, create_engine_and_session
from models.rating_model_model import FactorInputSource
from models.rating_instance_model import RatingFactorScore
from models.rating_model_model import RatingFactor, RatingModel
from models.statement_models import FinancialStatement
from models.rating_instance_model import RatingInstance
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

def test_rating_instance_creation():
    init_db(DB_NAME)

    # conv = fetch_conversation_with_messages(db, document_id)
    _, db = create_engine_and_session(DB_NAME)
    configure_rating_model_factors(db)
    app = FsApp(db)
    customer = app.create_statement_data_for_customer("CIF-123456")
    print(f"Created statement data for customer: {customer.customer_name}")
    template = db.query(Template).filter(Template.name == "FinTemplate").first()
    rating_model=get_or_create_rating_model(session=db,template=template,model_name='Corporate')
    statements = db.query(FinancialStatement).filter(FinancialStatement.customer_id == customer.id).all()
    statement_ids=  [schema.FinancialStatement.model_validate(statement).id for statement in statements]

    
    stmt_id=statement_ids[2]
    rating_instance=RatingInstance(customer_id=customer.id,financial_statement_id=stmt_id,rating_model_id=rating_model.id) 
    db.add(rating_instance)
    db.commit()
    db.flush()
    assert  rating_instance.id is not None


def test_rating_instance_processing():
    init_db(DB_NAME)

    # conv = fetch_conversation_with_messages(db, document_id)
    _, db = create_engine_and_session(DB_NAME)
    configure_rating_model_factors(db)
    app = FsApp(db)
    customer = app.create_statement_data_for_customer("CIF-123456")
    print(f"Created statement data for customer: {customer.customer_name}")
    template = db.query(Template).filter(Template.name == "FinTemplate").first()
    rating_model=get_or_create_rating_model(session=db,template=template,model_name='Corporate')
    statements = db.query(FinancialStatement).filter(FinancialStatement.customer_id == customer.id).all()
    statement_ids=  [schema.FinancialStatement.model_validate(statement).id for statement in statements]

    
    stmt_id=statement_ids[2]
    rating_instance=RatingInstance(customer_id=customer.id,financial_statement_id=stmt_id,rating_model_id=rating_model.id) 
    db.add(rating_instance)
    db.commit()
    db.flush()
    assert  rating_instance.id is not None
    process_rating_instance(db, rating_instance)

def test_completeness_of_quantitative():
    init_db(DB_NAME)

    # conv = fetch_conversation_with_messages(db, document_id)
    _, db = create_engine_and_session(DB_NAME)
    configure_rating_model_factors(db)
    app = FsApp(db)
    customer = app.create_statement_data_for_customer("CIF-123456")
    print(f"Created statement data for customer: {customer.customer_name}")
    template = db.query(Template).filter(Template.name == "FinTemplate").first()
    rating_model=get_or_create_rating_model(session=db,template=template,model_name='Corporate')
    statement = db.query(FinancialStatement).filter(FinancialStatement.customer_id == customer.id,FinancialStatement.financials_period_year==2023).first()
    # statement_ids=  [schema.FinancialStatement.model_validate(statement).id for statement in statements]

    # # Get statement pertaining to 2023 
    # stmt_id=  [schema.FinancialStatement.model_validate(statement).id for statement in statements if ][0]

    rating_instance=RatingInstance(customer_id=customer.id,financial_statement_id=statement.id,rating_model_id=rating_model.id) 
    db.add(rating_instance)
    db.commit()
    db.flush()
    assert  rating_instance.id is not None
    # check whether the model checks for completeness of financial information
    
    quant_factor_scores, incomplete_financial_information,missing_fields = get_quant_factor_inputs(db, rating_instance)
    print(missing_fields)
    assert incomplete_financial_information==False,'2023 all financials are available, hence thsi shoild be False'
   
    ### check for 2021,whcih doenst have all factors
    statement = db.query(FinancialStatement).filter(FinancialStatement.customer_id == customer.id,FinancialStatement.financials_period_year==2021).first()
    # statement_ids=  [schema.FinancialStatement.model_validate(statement).id for statement in statements]

    # # Get statement pertaining to 2023 
    # stmt_id=  [schema.FinancialStatement.model_validate(statement).id for statement in statements if ][0]

    rating_instance=RatingInstance(customer_id=customer.id,financial_statement_id=statement.id,rating_model_id=rating_model.id) 
    db.add(rating_instance)
    db.commit()
    db.flush()
    assert  rating_instance.id is not None
    # check whether the model checks for completeness of financial information
    
    quant_factor_scores, incomplete_financial_information,missing_fields = get_quant_factor_inputs(db, rating_instance)
    print(missing_fields)
    assert incomplete_financial_information==True,'2021 all financials are not available, hence thsi shoild be True'
    assert len(missing_fields)>1,'2021 all financials are not available, hence thsi shoild be several missing fields'
    
def test_quantitative_scoring():
    init_db(DB_NAME)

    # conv = fetch_conversation_with_messages(db, document_id)
    _, db = create_engine_and_session(DB_NAME)
    configure_rating_model_factors(db)
    app = FsApp(db)
    customer = app.create_statement_data_for_customer("CIF-123456")
    print(f"Created statement data for customer: {customer.customer_name}")
    template = db.query(Template).filter(Template.name == "FinTemplate").first()
    rating_model=get_or_create_rating_model(session=db,template=template,model_name='Corporate')
    statement = db.query(FinancialStatement).filter(FinancialStatement.customer_id == customer.id,FinancialStatement.financials_period_year==2023).first()
    # statement_ids=  [schema.FinancialStatement.model_validate(statement).id for statement in statements]

    # # Get statement pertaining to 2023 
    # stmt_id=  [schema.FinancialStatement.model_validate(statement).id for statement in statements if ][0]

    rating_instance=RatingInstance(customer_id=customer.id,financial_statement_id=statement.id,rating_model_id=rating_model.id) 
    db.add(rating_instance)
    db.commit()
    db.flush()
    assert  rating_instance.id is not None
    # check whether the model checks for completeness of financial information
    
    quant_factor_scores, incomplete_financial_information,missing_fields = get_quant_factor_inputs(db, rating_instance)
    print(missing_fields)
    assert incomplete_financial_information==False,'2023 all financials are available, hence thsi shoild be False'
   
    ### check for 2021,whcih doenst have all factors
    statement = db.query(FinancialStatement).filter(FinancialStatement.customer_id == customer.id,FinancialStatement.financials_period_year==2021).first()
    # statement_ids=  [schema.FinancialStatement.model_validate(statement).id for statement in statements]

    # # Get statement pertaining to 2023 
    # stmt_id=  [schema.FinancialStatement.model_validate(statement).id for statement in statements if ][0]

    rating_instance=RatingInstance(customer_id=customer.id,financial_statement_id=statement.id,rating_model_id=rating_model.id) 
    db.add(rating_instance)
    db.commit()
    db.flush()
    assert  rating_instance.id is not None
    # check whether the model checks for completeness of financial information
    
    quant_factor_scores, incomplete_financial_information,missing_fields = get_quant_factor_inputs(db, rating_instance)
    print(missing_fields)
    assert incomplete_financial_information==True,'2021 all financials are not available, hence thsi shoild be True'
    assert len(missing_fields)>1,'2021 all financials are not available, hence thsi shoild be several missing fields'
    
    