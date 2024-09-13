from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship, Session
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import List, Optional, Dict
import enum
from decimal import Decimal

from rating_model import configure_rating_model_factors, get_or_create_rating_model
from models.models import RatingFactorAttribute, RatingInstance,RatingFactorScore,RatingModel,RatingFactor,FinancialStatement,FactorInputSource



from customer_financial_statement import FsApp
# class RatingFactorScore(Base):
#     __tablename__ = 'rating_factor_scores'

#     id = Column(Integer, primary_key=True)
#     raw_value_text = Column(String)
#     raw_value_float = Column(Float)
#     score = Column(Float)
#     score_dirty = Column(Boolean, default=True)
#     rating_instance_id = Column(Integer, ForeignKey('rating_instances.id'))
#     rating_factor_name = Column(String, ForeignKey('rating_factors.name'))

#     rating_instance = relationship("RatingInstance", back_populates="factor_scores")
#     rating_factor = relationship("RatingFactor")

#     @classmethod
#     def new(cls, factor_value: FactorValue, rating_factor: RatingFactor, rating_instance_id: int):
#         return cls(
#             raw_value_text=factor_value.raw_value_text,
#             raw_value_float=factor_value.raw_value_float,
#             score=factor_value.score,
#             rating_factor=rating_factor,
#             rating_instance_id=rating_instance_id,
#             score_dirty=True
#         )

# class RatingFactorAttribute(Base):
#     __tablename__ = 'rating_factor_attributes'

#     id = Column(Integer, primary_key=True)
#     rating_model_id = Column(Integer, ForeignKey('rating_models.id'))
#     rating_factor_name = Column(String)
#     bin_start = Column(Float)
#     bin_end = Column(Float)
#     score = Column(Float)
#     # ... other fields ...

# class RatingInstance(Base):
#     __tablename__ = 'rating_instances'

#     id = Column(Integer, primary_key=True)
#     customer_id = Column(Integer, ForeignKey('customers.id'))
#     financials_period_id = Column(Integer, ForeignKey('financials_periods.id'))
#     rating_model_id = Column(Integer, ForeignKey('rating_models.id'))

#     customer = relationship("Customer")
#     financials_period = relationship("FinancialsPeriod")
#     rating_model = relationship("RatingModel")
#     factor_scores = relationship("RatingFactorScore", back_populates="rating_instance")

#     def score_quantitative_factors(self, session: Session, fs_app: 'FsApp'):
#         stmt = session.query(FinancialStatement).filter_by(
#             customer_id=self.customer.id,
#             financials_period_id=self.financials_period.id,
#             template=self.rating_model.template
#         ).first()

#         line_item_values = get_all_fields_values(session, stmt)
#         derived_quant_factors = []

#         def get_raw_factor_values():
#             if not self.quant_factors:
#                 self.quant_factors = self.rating_model.get_quantitative_factors(session, FactorInputSource.FINANCIAL_STATEMENT)

#             quant_factor_scores = []
#             for qf in self.quant_factors:
#                 if qf.input_source == FactorInputSource.FINANCIAL_STATEMENT:
#                     if qf.name not in line_item_values or line_item_values[qf.name] is None:
#                         raise ValueError(f"Missing value for factor: {qf.name}")
#                     raw_factor_value = FactorValue(raw_value_float=line_item_values[qf.name])
#                     rf_score = RatingFactorScore.new(raw_factor_value, qf, self.id)
#                     quant_factor_scores.append(rf_score)
#                 else:
#                     derived_quant_factors.append(qf)

#             return quant_factor_scores

#         self.quant_factor_scores = get_raw_factor_values()
#         derived_quant_factors.sort(key=lambda x: x.order_no)

#         factor_attributes = self.rating_model.get_factors_attributes(session)

#         def get_factor_wise_scores(rfs: RatingFactorScore):
#             return next(
#                 (attr for attr in factor_attributes
#                  if attr.rating_factor_name == rfs.rating_factor.name
#                  and attr.bin_start < rfs.raw_value_float <= attr.bin_end),
#                 None
#             )

#         for index, qf in enumerate(self.quant_factor_scores):
#             attrib = get_factor_wise_scores(qf)
#             if attrib:
#                 self.quant_factor_scores[index].score = attrib.score

#         # Score the derived variables
#         print(self.factor_scores_map)


# def get_factor_score(fs_app: FsApp, factor_name: str, rating_instance_id: int) -> RatingFactorScore:
#     return (fs_app.session.query(RatingFactorScore)
#             .filter_by(rating_instance_id=rating_instance_id, rating_factor_name=factor_name)
#             .first())

# Usage example
def score_quantitative_factors(db,rating_instance: RatingInstance) -> None:
        # Fetch the financial statement
        stmt = db.query(FinancialStatement).filter(
            FinancialStatement.customer_id == rating_instance.customer_id,
            FinancialStatement.id == rating_instance.financial_statement_id,
            FinancialStatement.template_id == rating_instance.rating_model.template_id
        ).first()

        if not stmt:
            raise ValueError("No matching financial statement found")
        app = FsApp(db)
        # Get line item values from the statement
        line_item_values = app.get_all_fields_values(stmt)

        derived_quant_factors = []

        def get_raw_factor_values() -> List[RatingFactorScore]:
            quant_factors = db.query(RatingFactor).filter(
                RatingFactor.rating_model_id == rating_instance.rating_model_id,
                RatingFactor.factor_type == 'quantitative'
            ).all()

            quant_factor_scores = []
            for qf in quant_factors:
                if qf.input_source == FactorInputSource.FINANCIAL_STATEMENT.value:
                    if qf.name not in line_item_values or line_item_values[qf.name] is None:
                        raise ValueError(f"Missing value for factor: {qf.name}")
                    
                    raw_factor_value = line_item_values[qf.name]
                    rf_score = RatingFactorScore(
                        rating_instance_id=rating_instance.id,
                        rating_factor_id=qf.id,
                        raw_value_float=raw_factor_value.value,
                        score_dirty=True
                    )
                    quant_factor_scores.append(rf_score)
                else:
                    derived_quant_factors.append(qf)

            return quant_factor_scores

        quant_factor_scores = get_raw_factor_values()
        db.add_all(quant_factor_scores)
        db.flush()

        # Sort derived quantitative factors
        derived_quant_factors.sort(key=lambda x: x.order_no)

        # Get factor attributes
        factor_attributes = db.query(RatingFactorAttribute).filter(
            RatingFactorAttribute.rating_model_id == rating_instance.rating_model_id
        ).all()

        def get_factor_wise_scores(rfs: RatingFactorScore) -> RatingFactorAttribute:
            return next(
                (attr for attr in factor_attributes
                 if attr.rating_factor_id == rfs.rating_factor_id
                 and attr.bin_start < rfs.raw_value_float <= attr.bin_end),
                None
            )

        # Calculate scores
        for rfs in quant_factor_scores:
            attrib = get_factor_wise_scores(rfs)
            if attrib:
                rfs.score = attrib.score

        db.add_all(quant_factor_scores)
        db.commit()

        # TODO: Handle derived factors here

        print("Quantitative factors scored successfully")

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
    print(rating_factor_values)

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

def update_qualitative_factor_scores(db: Session, rating_instance: RatingInstance):
    # Get all RatingFactorScore entries for this rating instance
    factor_scores = db.query(RatingFactorScore).filter(
        RatingFactorScore.rating_instance_id == rating_instance.id
    ).all()

    # Get all RatingFactorAttribute entries for this rating model
    factor_attributes = db.query(RatingFactorAttribute).filter(
        RatingFactorAttribute.rating_model_id == rating_instance.rating_model_id
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

if __name__ == "__main__":
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models.models import Template,FinancialStatement
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
    statements = db.query(FinancialStatement).filter(FinancialStatement.customer_id == customer.id).all()
    statement_ids=  [schema.FinancialStatement.model_validate(statement).id for statement in statements]
    #initiate rating model instance
    stmt_id=statement_ids[2]
    rating_instance=RatingInstance(customer_id=customer.id,financial_statement_id=stmt_id,rating_model_id=rating_model.id) 
    db.add(rating_instance)
    db.commit()
    db.flush()
    score_quantitative_factors(db=db,rating_instance=rating_instance)
    generate_qualitative_factor_data(db,rating_instance=rating_instance)
    update_qualitative_factor_scores(db, rating_instance)

        # rating_model_app.check_quant_factors_presence_in_financial_template(
        #     rating_model)