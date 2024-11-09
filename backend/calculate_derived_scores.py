from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Dict, List, Optional,Tuple
from models.rating_model_model import FactorInputSource, ScoreToGradeMapping
from models.statement_models import Template
from models.rating_instance_model import RatingFactorScore
from models.rating_model_model import RatingFactor, RatingModel
from models.statement_models import FinancialStatement
from models.rating_instance_model import RatingInstance
from models.rating_model_model import RatingFactorAttribute
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship, Session
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import List, Optional, Dict
import enum
from decimal import Decimal

from rating_model import configure_rating_model_factors, get_or_create_rating_model



from py_expression_eval import Parser

class FactorNode:
    def __init__(self, factor: RatingFactor):
        self.factor = factor
        self.children: List[FactorNode] = []
        self.parent: Optional[FactorNode] = None

class DerivedFactor(BaseModel):
        id : str
        factor_name:str
        new_score :float
def calculate_derived_scores(db: Session, rating_instance: RatingInstance) -> Tuple[Dict[str, float], List[DerivedFactor]]:
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
            if fs.rating_factor.input_source != 'derived':
                env[fs.rating_factor.name] = fs.score

    # Filter for derived fields and create a dictionary
    derived_factors = {rf.name: rf for rf in rating_factors if rf.input_source == 'derived'}

    # Function to determine the derivation order of a factor
    def get_derivation_order(factor: RatingFactor, visited: set) -> int:
        if factor.name in visited:
            raise ValueError(f"Circular dependency detected for factor: {factor.name}")
        
        visited.add(factor.name)
        
        if not factor.formula:
            return 0
        
        max_child_order = 0
        for child_name in derived_factors:
            if child_name in factor.formula:
                child_order = get_derivation_order(derived_factors[child_name], visited.copy())
                max_child_order = max(max_child_order, child_order)
        
        return max_child_order + 1

    # Assign derivation order to each derived factor
    for factor in derived_factors.values():
        factor.derivation_order = get_derivation_order(factor, set())

    # Sort derived factors by derivation order
    sorted_derived_factors = sorted(derived_factors.values(), key=lambda x: x.derivation_order)

    parser = Parser()
    derived_factor_results: List[DerivedFactor] = []

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

    # Calculate scores for derived factors in order
    for factor in sorted_derived_factors:
        score = calculate_score(factor)
        if score is not None:
            updated_factor_score = update_or_create_score(db, rating_instance.id, factor.id, score)
            env[factor.name] = score
            derived_factor_results.append(DerivedFactor(id=str(updated_factor_score.id), factor_name=factor.name, new_score=score))

    db.commit()
    if 'overallScore' in env:
        overall_score = env['overallScore']
        rating_instance.overall_score = overall_score

        # Get the corresponding grade from ScoreToGradeMapping
        grade_mapping = db.query(ScoreToGradeMapping).filter(
            ScoreToGradeMapping.rating_model_id == rating_instance.rating_model_id,
            ScoreToGradeMapping.bin_start <= overall_score,
            ScoreToGradeMapping.bin_end > overall_score
        ).first()

        if grade_mapping:
            rating_instance.overall_rating = grade_mapping.grade
        else:
            print(f"Warning: No grade mapping found for score {overall_score}")

    db.add(rating_instance)
    db.commit()
    return env, derived_factor_results
# def calculate_derived_scores(db: Session, rating_instance: RatingInstance) -> Tuple[Dict[str, float], List[DerivedFactor]]:
#     # Get all RatingFactors for this rating model
#     rating_factors = db.query(RatingFactor).filter(
#         RatingFactor.rating_model_id == rating_instance.rating_model_id
#     ).all()

#     # Get all RatingFactorScores for this rating instance
#     factor_scores = db.query(RatingFactorScore).filter(
#         RatingFactorScore.rating_instance_id == rating_instance.id
#     ).all()

#     # Create a dictionary of factor scores for easy lookup,that are not
#     env: Dict[str, float] = {}
#     for fs in factor_scores:
#         if fs.score is not None:
#             if fs.rating_factor.input_source != 'derived':
#                 env[fs.rating_factor.name] = fs.score

#     # Create a dictionary of factors for easy lookup
#     factor_dict: Dict[str, FactorNode] = {rf.name: FactorNode(rf) for rf in rating_factors}

#     # Build the factor hierarchy
#     root_nodes: List[FactorNode] = []
#     for factor in rating_factors:
#         node = factor_dict[factor.name]
#         if not factor.parent_factor_name:
#             root_nodes.append(node)
#         else:
#             parent_node = factor_dict.get(factor.parent_factor_name)
#             if parent_node:
#                 parent_node.children.append(node)
#                 node.parent = parent_node
#     parser = Parser()
#     derived_factors: List[DerivedFactor] = []

#     def calculate_score(factor: RatingFactor) -> Optional[float]:
#         if not factor.formula:
#             return None
#         try:
#             expression = parser.parse(factor.formula)
#             result = expression.evaluate(env)
#             return float(result)
#         except Exception as e:
#             print(f"Error calculating score for {factor.name}: {str(e)}")
#             return None

#     def process_node(node: FactorNode):
#         # First, process all children if not already processed
#         for child in node.children:
#             if child.factor.name not in env:
#                 process_node(child)

#         # Then, calculate the score for this node if it's derived
#         if node.factor.input_source == 'derived':
#             score = calculate_score(node.factor)
#             if score is not None:
#                 updated_factor_score= update_or_create_score(db, rating_instance.id, node.factor.id, score)
#                 env[node.factor.name] = score
#                 derived_factors.append(DerivedFactor(id=str(updated_factor_score.id), factor_name=node.factor.name,new_score=score))

#     # Start processing from leaf nodes
#     leaf_nodes = [node for node in factor_dict.values() if not node.children]
#     for leaf in leaf_nodes:
#         process_node(leaf)

#     # Process any remaining nodes (in case there are disconnected nodes)
#     for node in factor_dict.values():
#         if node.factor.name not in env:
#             process_node(node)

#     db.commit()
#     return env, derived_factors

def update_or_create_score(db: Session, rating_instance_id: int, factor_id: str, score: float) -> RatingFactorScore:
    factor_score = db.query(RatingFactorScore).filter(
        RatingFactorScore.rating_instance_id == rating_instance_id,
        RatingFactorScore.rating_factor_id == factor_id
    ).first()

    if factor_score:
        factor_score.score = score
        factor_score.score_dirty = False  # Assuming you have this field to indicate the score has been updated
    else:
        factor_score = RatingFactorScore(
            rating_instance_id=rating_instance_id,
            rating_factor_id=factor_id,
            score=score,
            score_dirty=False
        )
        db.add(factor_score)
    
    try:
        db.commit()
        db.refresh(factor_score)
    except Exception as e:
        db.rollback()
        print(f"Error updating or creating score: {str(e)}")
        raise

    return factor_score
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
    score_quantitative_factors(db=db,rating_instance=rating_instance)
    generate_qualitative_factor_data(db,rating_instance=rating_instance)
    update_qualitative_factor_scores(db, rating_instance)
    final_scores, derived_factors = calculate_derived_scores(db, rating_instance)
    print("Final scores:", final_scores)
    for d in derived_factors:
        print(d.factor_name,d.new_score)