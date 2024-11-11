from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, and_
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import relationship, Session
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import List, Optional, Dict
import enum
from decimal import Decimal

from models.statement_models import Template
from models.rating_instance_model import RatingFactorScore
from models.rating_model_model import RatingFactor, RatingFactorAttribute, RatingModel
from models.statement_models import FinancialStatement
from models.rating_instance_model import RatingInstance
from rating_model import configure_rating_model_factors, get_or_create_rating_model

from typing import List, Tuple
from sqlalchemy.orm import Session
from uuid import UUID


from customer_financial_statement import FsApp


def generate_qualitative_factor_data(db: Session, rating_instance: RatingInstance):
    rating_factor_values: Dict[str, str] = {
        "industry_outlook": "Positive",
        "mkt_segment": "High Growth",
        "governmentPolicies": "Neutral",
        "mkt_competence": "High",
        "promoter_track": "Good",
        "customer_concentration": "Highly Diversified",
        "capacity_utilisation": "In line with Industry",
        "cost_efficiency": "In line with industry",
        "technology_employed": "In line with Industry Standards",
        "other_financial_sources": "2 of the above",
    }

    # Assuming you have a method to get qualitative factors
    # rating_instance.rating_model.get_qualitative_factors(app, enums.USER_INPUT)
    rating_factors = db.query(RatingFactor).filter(
        RatingFactor.rating_model_id == rating_instance.rating_model_id
    ).all()
    rating_factor_map = {rf.name: rf for rf in rating_factors} 
    rating_factors = db.query(RatingFactor).filter(
        RatingFactor.rating_model_id == rating_instance.rating_model_id
    ).all()
    rating_factor_map = {rf.name: rf for rf in rating_factors}

    factor_scores = []
    for factor_name, value in rating_factor_values.items():
        print(f"factor = {factor_name} : {value}")
        rating_factor = rating_factor_map.get(factor_name)
        if rating_factor:
            factor_scores.append(RatingFactorScore(
                rating_instance_id=rating_instance.id,
                rating_factor_id=rating_factor.id,
                raw_value_text=value,
                score_dirty=True
            ))
        else:
            print(f"Warning: RatingFactor '{factor_name}' not found for this rating model")

    db.add_all(factor_scores)
    db.commit()

def initiate_qualitative_factor_data(db: Session, rating_instance: RatingInstance):
    ## this will initiate the rating instance, by adding all qualitative fields that are needed in the RatingFactorScore table
    ## it will initiate with NULL
    rating_factors = db.query(RatingFactor).filter(
        RatingFactor.rating_model_id == rating_instance.rating_model_id
    ).all()
    rating_factors = db.query(RatingFactor).filter(
        RatingFactor.rating_model_id == rating_instance.rating_model_id
    ).all()
    factor_scores = []
    for rating_factor in rating_factors:
            factor_scores.append(RatingFactorScore(
                rating_instance_id=rating_instance.id,
                rating_factor_id=rating_factor.id,
                score_dirty=True
            ))
    db.add_all(factor_scores)
    db.commit()

def update_qualitative_factor_scores(db: Session, rating_instance: RatingInstance):
    # Get all RatingFactorScore entries for this rating instance
    factor_scores = db.query(RatingFactorScore).filter(
        RatingFactorScore.rating_instance_id == rating_instance.id
    ).all()

    # Get all RatingFactorAttribute entries for this rating model
    factor_attributes = db.query(RatingFactorAttribute).filter(
        RatingFactorAttribute.rating_model_id == rating_instance.rating_model_id
    ).filter(
        RatingFactorAttribute.attribute_type == 'lookup'
    ).all()

    # Create a dictionary for quick lookup of RatingFactorAttributes
    attribute_map: Dict[tuple, RatingFactorAttribute] = {
        (attr.rating_factor_id, attr.label): attr for attr in factor_attributes
    }

    # Update scores for each RatingFactorScore
    for factor_score in factor_scores:
        attribute_key = (factor_score.rating_factor_id, factor_score.raw_value_text)
        matching_attribute = attribute_map.get(attribute_key)
        
        if matching_attribute:
            factor_score.score = matching_attribute.score
            factor_score.score_dirty = False
        else:
            print(f"Warning: No matching attribute found for factor {factor_score.rating_factor.name} with value {factor_score.raw_value_text}")
            factor_score.score_dirty = True

    # Commit the changes
    db.commit()
# Assuming these are defined elsewhere in your code

class FactorInputSource:
    FINANCIAL_STATEMENT = "financial_statement"
    USER_INPUT = "user_input"


def get_quant_factor_inputs(db: Session, rating_instance: RatingInstance) -> Tuple[List[RatingFactorScore], bool]:
    stmt = db.query(FinancialStatement).filter(
        FinancialStatement.id == rating_instance.financial_statement_id
    ).first()
    if not stmt:
        raise ValueError("No matching financial statement found")
    
    app = FsApp(db)
    line_item_values = app.get_all_fields_values(stmt)
    
    quant_factors = db.query(RatingFactor).filter(
        RatingFactor.rating_model_id == rating_instance.rating_model_id,
        RatingFactor.factor_type == 'quantitative'
    ).all()
    
    missing_fields = []
    updated_or_new_scores = []
    
    for qf in quant_factors:
        if qf.input_source == FactorInputSource.FINANCIAL_STATEMENT:
            if qf.name not in line_item_values or line_item_values[qf.name].valid is False:
                missing_fields.append(qf.name)
            else:
                raw_factor_value = line_item_values[qf.name]
                
                # Check if a score already exists for this rating instance and factor
                existing_score = db.query(RatingFactorScore).filter(
                    and_(
                        RatingFactorScore.rating_instance_id == rating_instance.id,
                        RatingFactorScore.rating_factor_id == qf.id
                    )
                ).first()
                
                if existing_score:
                    # Update existing score
                    existing_score.raw_value_float = raw_factor_value.value
                    existing_score.score_dirty = True
                    updated_or_new_scores.append(existing_score)
                else:
                    # Create new score
                    new_score = RatingFactorScore(
                        rating_instance_id=rating_instance.id,
                        rating_factor_id=qf.id,
                        raw_value_float=raw_factor_value.value,
                        score_dirty=True,
                    )
                    updated_or_new_scores.append(new_score)
    
    incomplete_financial_information = len(missing_fields) > 0
    
    if incomplete_financial_information:
        rating_instance.missing_financial_fields = missing_fields
        rating_instance.incomplete_financial_information = True
    else:
        rating_instance.missing_financial_fields = []
        rating_instance.incomplete_financial_information = False
        
        # Add all updated or new scores to the session
        for score in updated_or_new_scores:
            db.merge(score)  # This will insert new or update existing scores
    
    db.add(rating_instance)
    db.flush()
    
    return updated_or_new_scores, incomplete_financial_information,missing_fields

def check_all_user_inputs_factor_availability(db: Session, rating_instance: RatingInstance) -> bool:
    user_input_factors = db.query(RatingFactor).filter(
        RatingFactor.rating_model_id == rating_instance.rating_model_id,
        RatingFactor.input_source == FactorInputSource.USER_INPUT
    ).all()

    factor_scores = db.query(RatingFactorScore).filter(
        RatingFactorScore.rating_instance_id == rating_instance.id,
        RatingFactorScore.rating_factor_id.in_([f.id for f in user_input_factors])
    ).all()

    all_inputs_available = len(user_input_factors) == len(factor_scores)

    if all_inputs_available:
        rating_instance.inputs_completion_status = True
        db.commit()

    return all_inputs_available


def score_quantitative_factors(db: Session, rating_instance: RatingInstance) -> None:
    if rating_instance.incomplete_financial_information:
        print("Incomplete financial information. Skipping scoring.")
        return


    # factor_scores = db.query(RatingFactorScore).filter(
    #     RatingFactorScore.rating_instance_id == rating_instance.id,
    # ).all()
    quant_factor_scores = db.query(RatingFactorScore).join(RatingFactor).filter(
        and_(
            RatingFactorScore.rating_instance_id == rating_instance.id,
            RatingFactor.factor_type == 'quantitative'
        )
    ).options(joinedload(RatingFactorScore.rating_factor)).all()
    
    factor_attributes = db.query(RatingFactorAttribute).filter(
            RatingFactorAttribute.rating_model_id == rating_instance.rating_model_id
        ).all()

    def get_factor_wise_scores(rfs: RatingFactorScore) -> RatingFactorAttribute:
        return next(
            (attr for attr in factor_attributes
             if  attr.rating_factor_id == rfs.rating_factor_id
             and attr.bin_start < rfs.raw_value_float <= attr.bin_end),
            None
        )

    for rfs in quant_factor_scores:
        attrib = get_factor_wise_scores(rfs)
        if attrib:
            rfs.score = attrib.score
            rfs.score_dirty = False

    db.add_all(quant_factor_scores)
    db.commit()

    print("Quantitative factors scored successfully")


# def process_rating_instance(db: Session, rating_instance: RatingInstance):
#     try:
#         quant_factor_scores, incomplete_financial_information,missing_fields = get_quant_factor_inputs(db, rating_instance)
        
#         if incomplete_financial_information:
#             rating_instance.incomplete_financial_information = True
#             db.commit()
#             print("Incomplete financial information. No further processing.")
#             return

#         if check_all_user_inputs_factor_availability(db, rating_instance):
#             score_quantitative_factors(db, rating_instance)
#             update_qualitative_factor_scores(db, rating_instance)
#             calculate_derived_scores(db,rating_instance)
            
#         else:
#             print("Not all user inputs are available. Waiting for completion.")

#     except Exception as e:
#         print(f"Error processing rating instance: {str(e)}")
#         # Handle the error appropriately (e.g., logging, rolling back transaction)

if __name__ == "__main__":
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models.rating_model_model import ScoreToGradeMapping
    from schema import schema

    from main import create_engine_and_session, DB_NAME,init_db
    from customer_financial_statement import FsApp
    init_db(DB_NAME)
    _, db = create_engine_and_session(DB_NAME)
    configure_rating_model_factors(db)
    app = FsApp(db)
    customer = app.create_statement_data_for_customer("CIF-123456")
    print(f"Created statement data for customer: {customer.customer_name}")
    template = db.query(Template).filter(Template.name == "FinTemplate").first()
    rating_model=get_or_create_rating_model(session=db,template=template,model_name='Corporate')
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

    # Create ScoreToGradeMapping objects
    mappings = [
        ScoreToGradeMapping(
            rating_model_id=rating_model.id,
            bin_start=start,
            bin_end=end,
            grade=str(grade)
        )
        for start, end, grade in mapping_data
    ]

    # Add all mappings to the session and commit
    db.add_all(mappings)
    db.commit()
    statements = db.query(FinancialStatement).filter(FinancialStatement.customer_id == customer.id).all()
    statement_ids=  [schema.FinancialStatement.model_validate(statement).id for statement in statements]
    #initiate rating model instance
    stmt_id=statement_ids[2]
    rating_instance=RatingInstance(customer_id=customer.id,financial_statement_id=stmt_id,rating_model_id=rating_model.id) 
    db.add(rating_instance)
    db.commit()
    db.flush()
    # process_rating_instance(db, rating_instance)
