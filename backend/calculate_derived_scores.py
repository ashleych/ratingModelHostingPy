from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Dict, List, Optional
from rating_model_instance import generate_qualitative_factor_data, score_quantitative_factors, update_qualitative_factor_scores
from models.models import RatingFactor,RatingFactorAttribute,RatingFactorScore
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
from py_expression_eval import Parser

class FactorNode:
    def __init__(self, factor: RatingFactor):
        self.factor = factor
        self.children: List[FactorNode] = []
        self.parent: Optional[FactorNode] = None

def calculate_derived_scores(db: Session, rating_instance: RatingInstance):
    # Get all RatingFactors for this rating model
    rating_factors = db.query(RatingFactor).filter(
        RatingFactor.rating_model_id == rating_instance.rating_model_id
    ).all()

    # Get all RatingFactorScores for this rating instance
    factor_scores = db.query(RatingFactorScore).filter(
        RatingFactorScore.rating_instance_id == rating_instance.id
    ).all()

    # Create a dictionary of factor scores for easy lookup
    env: Dict[str, float] = {}
    for fs in factor_scores:
        if fs.score is not None:
            env[fs.rating_factor.name] = fs.score

    # Create a dictionary of factors for easy lookup
    factor_dict: Dict[str, FactorNode] = {rf.name: FactorNode(rf) for rf in rating_factors}

    # Build the factor hierarchy
    root_nodes: List[FactorNode] = []
    for factor in rating_factors:
        node = factor_dict[factor.name]
        if not factor.parent_factor_name:
            root_nodes.append(node)
        else:
            parent_node = factor_dict.get(factor.parent_factor_name)
            if parent_node:
                parent_node.children.append(node)
                node.parent = parent_node

    parser = Parser()

    def calculate_score(factor: RatingFactor) -> Optional[float]:
        if not factor.formula:
            return None
        try:
            expression = parser.parse(factor.formula)
            result = expression.evaluate(env)
            return float(result)
        except Exception as e:
            print(f"Error calculating score for {factor.name}: {str(e)}")
            return None

    def process_node(node: FactorNode):
        # First, process all children if not already processed
        for child in node.children:
            if child.factor.name not in env:
                process_node(child)

        # Then, calculate the score for this node if it's derived
        if node.factor.input_source == 'derived':
            score = calculate_score(node.factor)
            if score is not None:
                update_or_create_score(db, rating_instance.id, node.factor.id, score)
                env[node.factor.name] = score

    # Start processing from leaf nodes
    leaf_nodes = [node for node in factor_dict.values() if not node.children]
    for leaf in leaf_nodes:
        process_node(leaf)

    # Process any remaining nodes (in case there are disconnected nodes)
    for node in factor_dict.values():
        if node.factor.name not in env:
            process_node(node)

    db.commit()
    return env

def update_or_create_score(db: Session, rating_instance_id: int, rating_factor_id: int, score: float):
    factor_score = db.query(RatingFactorScore).filter(
        and_(
            RatingFactorScore.rating_instance_id == rating_instance_id,
            RatingFactorScore.rating_factor_id == rating_factor_id
        )
    ).first()

    if factor_score:
        factor_score.score = score
        factor_score.score_dirty = False
    else:
        new_score = RatingFactorScore(
            rating_instance_id=rating_instance_id,
            rating_factor_id=rating_factor_id,
            score=score,
            score_dirty=False
        )
        db.add(new_score)

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
    final_scores = calculate_derived_scores(db, rating_instance)
    print("Final scores:", final_scores)