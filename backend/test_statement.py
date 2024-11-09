
from pathlib import Path
from fastapi.testclient import TestClient
from typing import List
import sys
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker



# sys.path.insert(1, "/home/ashleyubuntu/ratingModelPython/backend")
from app import app
from models.rating_model_model import FactorInputSource
from models.rating_instance_model import RatingFactorScore
from models.rating_model_model import RatingFactor, RatingModel
from models.statement_models import FinancialStatement, LineItemMeta, LineItemValue
from models.rating_instance_model import RatingInstance
from schema import schema
client = TestClient(app)


from schema import schema
from models import models
import pprint
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.statement_models import Template
from schema import schema

from main import create_engine_and_session, DB_NAME,init_db
from customer_financial_statement import FsApp
from models.rating_instance_model import RatingInstance
from rating_model import configure_rating_model_factors, get_or_create_rating_model
from models.models import RatingFactorAttribute
from   rating_model_instance import process_rating_instance,get_quant_factor_inputs

def test_rating_statemetn_creation():
    init_db(DB_NAME)

    # conv = fetch_conversation_with_messages(db, document_id)
    _, db = create_engine_and_session(DB_NAME)
    configure_rating_model_factors(db)
    app = FsApp(db)
    customer = app.create_statement_data_for_customer("CIF-123456")
    print(f"Created statement data for customer: {customer.customer_name}")
    template = db.query(Template).filter(Template.name == "FinTemplate").first()
     ### check for 2021,whcih doenst have all factors
    statement = db.query(FinancialStatement).filter(FinancialStatement.customer_id == customer.id,FinancialStatement.financials_period_year==2021).first()

    ## check if the lag values corresponding to this statemnet are all Nulls
    lag_metas = db.query(LineItemMeta).filter(
                LineItemMeta.template_id == statement.template_id,
                LineItemMeta.lag_months > 0
            ).all()
    for l in lag_metas:
        lineItemValue = db.query(LineItemValue).filter(LineItemValue.financial_statement_id == statement.id,LineItemValue.line_item_meta_id==l.id).first()
        assert lineItemValue.value is None
        
    