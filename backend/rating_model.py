from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship, Session
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import List, Optional
import csv
import enum
from schema import schema
from models.models import Template, RatingModel, RatingFactor, RatingFactorAttribute, RatingInstance, FactorInputSource

from models.base import Base
from models.models import FactorType,AttributeType
# Add other methods as needed

# You'll need to implement the Template model and other necessary models

import os
# Add other fields as needed

# You'll need to implement the FsApp class with necessary database connection methods


class RatingModule(BaseModel):
    module_name: str
    module_factor: schema.RatingFactor
    child_factors_in_module: List[schema.RatingFactor]


class RatingModelApp:
    def __init__(self, session: Session):
        self.session = session

    def update_formula_to_db(self, rating_model: RatingModel, factors):
        if isinstance(factors, RatingFactor):
            self.session.add(factors)
        elif isinstance(factors, list):
            self.session.add_all(factors)
        else:
            raise ValueError("Unsupported type being saved")
        self.session.commit()

    # def configure_scoring_factors_meta_from_csv(self, rating_model: RatingModel, filepath: str) -> List[RatingFactor]:
    #     factors = []
    #     with open(filepath, 'r') as csvfile:
    #         reader = csv.DictReader(csvfile)
    #         for row in reader:
    #             factor = RatingFactor(
    #                 name=row['name'],
    #                 label=row['label'],
    #                 input_source=FactorInputSource[row['input_source'].upper(
    #                 )].value,
    #                 order_no=int(row['order_no']),
    #                 factor_type=FactorType[row['factor_type'].upper()].value,
    #                 parent_factor_name=row['parent_factor'],
    #                 weightage=float(row['Weightage']),
    #                 module=bool(int(row['module'])),
    #                 rating_model_id=rating_model.id
    #             )
    #             factors.append(factor)
    #     return factors

    # def configure_attributes_scoring_from_csv(self, rating_model: RatingModel, filepath: str) -> List[RatingFactorAttribute]:
    #     attributes = []
    #     with open(filepath, 'r') as csvfile:
    #         reader = csv.DictReader(csvfile)
    #         for row in reader:
    #             attribute = RatingFactorAttribute(
    #                 rating_model_id=rating_model.id,
    #                 rating_factor_name=row['factor'],
    #                 name=row['attribute_name'],
    #                 label=row['attribute_label'],
    #                 attribute_type=AttributeType[row['scoring_type'].upper()].value,
    #                 bin_start=float(
    #                     row['bin_start']) if row['bin_start'] else None,
    #                 bin_end=float(row['bin_end']) if row['bin_end'] else None,
    #                 score=float(row['score'])
    #             )
    #             attributes.append(attribute)
    #     return attributes

    def get_factors_attributes(self, rating_model: RatingModel) -> List[RatingFactorAttribute]:
        return self.session.query(RatingFactorAttribute).filter_by(rating_model_id=rating_model.id).all()
    def get_all_factors(self, rating_model: RatingModel) -> List[RatingFactor]:
        return self.session.query(RatingFactor).filter_by(rating_model_id=rating_model.id).all()
    def get_formulae_from_weightages(self, rating_model: RatingModel):
        def find_immediate_children(factor: RatingFactor, all_factors: List[RatingFactor]) -> List[RatingFactor]:
            return [child for child in all_factors if child.parent_factor_name == factor.name]

        factors = self.get_all_factors(rating_model)
        updated_factors = []

        for factor in factors:
            if factor.input_source == FactorInputSource.DERIVED.value:
                children = find_immediate_children(factor, factors)
                if children:
                    formula = " + ".join([f"{child.weightage} * {child.name}" for child in children])
                    if factor.formula != formula:
                        factor.formula = formula
                        updated_factors.append(factor)
                        self.session.add(factor)

        if updated_factors:
            self.session.commit()
            for factor in updated_factors:
                self.session.refresh(factor)

        return factors
    def check_quant_factors_presence_in_financial_template(self, rating_model: RatingModel):
        quant_factors = self.get_quantitative_factors(
            rating_model, FactorInputSource.FINANCIAL_STATEMENT.value)
        line_items = self.get_financial_template_line_items(
            rating_model.template)

        quant_names = set(factor.name for factor in quant_factors)
        line_item_names = set(item.name for item in line_items)

        diff = quant_names - line_item_names
        if diff:
            raise ValueError(
                "Factors defined as sourced from financial template not present in template")

    def get_quantitative_factors(self, rating_model: RatingModel, input_source: Optional[FactorInputSource] = None) -> List[RatingFactor]:
        query = self.session.query(RatingFactor).filter_by(
            rating_model_id=rating_model.id, factor_type=FactorType.QUANTITATIVE.value)
        if input_source:
            query = query.filter_by(input_source=input_source)
        return query.all()

    def get_qualitative_factors(self, rating_model: RatingModel, input_source: Optional[FactorInputSource] = None) -> List[RatingFactor]:
        query = self.session.query(RatingFactor).filter_by(
            rating_model_id=rating_model.id, factor_type=FactorType.QUALITATIVE.value)
        if input_source:
            query = query.filter_by(input_source=input_source)
        return query.all()

    def organise_factors_in_modules(self, rating_model: RatingModel, factor_type: FactorType) -> List[RatingModule]:
        factors = self.get_quantitative_factors(
            rating_model) if factor_type == FactorType.QUANTITATIVE.value else self.get_qualitative_factors(rating_model)

        modules = [RatingModule(module_name=factor.name, module_factor=factor, child_factors_in_module=[])
                   for factor in factors if factor.module]

        for module in modules:
            module.child_factors_in_module = [
                f for f in factors if f.parent_factor_name == module.module_name]

        return modules

    def get_financial_template_line_items(self, template: Template):
        # Implement this method to get line items for a template
        pass

def create_new_rating_model(session, template, model_name):
    new_rating_model = RatingModel(
        name=model_name,
        label=model_name,
        template_id=template.id
    )
    session.add(new_rating_model)
    try:
        session.flush()
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error creating new RatingModel: {str(e)}")
        raise
    
    return new_rating_model

def get_or_create_rating_model(session, template,model_name):
    try:
        rating_model = session.query(RatingModel).filter(RatingModel.name == model_name).first()
        
        if rating_model is None:
            # No exception, but no rating model found
            rating_model = create_new_rating_model(session, template,model_name)
    except Exception as e:
        # Handle any exceptions that might occur during the query
        print(f"An error occurred while querying RatingModel: {str(e)}")
        rating_model = create_new_rating_model(session, template,model_name)
    
    return rating_model

def configure_rating_model_factors(db):
    with db as session:
        files_dir='/home/ashleyubuntu/ratingModelPython/backend/Template-Basic/'
        model_definition_fn=os.path.join(files_dir,'CorporateModelDefinition.csv')
        rating_model_app = RatingModelApp(session)
        template = session.query(Template).filter(Template.name == "FinTemplate").first()
        rating_model=get_or_create_rating_model(session=session,template=template,model_name='Corporate')
        factors = configure_scoring_factors_meta_from_csv(
            rating_model, model_definition_fn)
        session.add_all(factors)
        session.flush()
        session.commit()

        attributes = configure_attributes_scoring_from_csv(factors,
            rating_model, os.path.join(files_dir,"CorporateModelDefinition-attributes.csv"))
        session.add_all(attributes)
        session.commit()

        rating_model_app.get_formulae_from_weightages(rating_model)
    
     
def configure_scoring_factors_meta_from_csv(rating_model: RatingModel, filepath: str) -> List[RatingFactor]:
        factors = []
        with open(filepath, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                factor = RatingFactor(
                    name=row['name'],
                    label=row['label'],
                    input_source=FactorInputSource[row['input_source'].upper()].value,
                    order_no=int(row['order_no']),
                    factor_type=FactorType[row['factor_type'].upper()].value,
                    parent_factor_name=row['parent_factor'],
                    weightage=float(row['Weightage']),
                    module=bool(int(row['module'])),
                    rating_model_id=rating_model.id
                )
                factors.append(factor)
        
        # Add factors to the database and flush to get their IDs
        # db.add_all(factors)
        # db.flush()
        
        return factors

def configure_attributes_scoring_from_csv(factors:List[RatingFactor],rating_model: RatingModel, filepath: str) -> List[RatingFactorAttribute]:
        # First, get all RatingFactors for this model
        # factors = db.query(RatingFactor).filter(RatingFactor.rating_model_id == rating_model.id).all()
        factor_map = {factor.name: factor.id for factor in factors}

        attributes = []
        with open(filepath, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                factor_name = row['factor']
                factor_id = factor_map.get(factor_name)
                if not factor_id:
                    raise ValueError(f"No matching RatingFactor found for: {factor_name}")

                attribute = RatingFactorAttribute(
                    rating_model_id=rating_model.id,
                    rating_factor_id=factor_id,
                    rating_factor_name=factor_name,
                    name=row['attribute_name'],
                    label=row['attribute_label'],
                    attribute_type=AttributeType[row['scoring_type'].upper()].value,
                    bin_start=float(row['bin_start']) if row['bin_start'] else None,
                    bin_end=float(row['bin_end']) if row['bin_end'] else None,
                    score=float(row['score'])
                )
                attributes.append(attribute)
        
        return attributes

def configure_rating_model_from_csv(self, rating_model: RatingModel, factors_filepath: str, attributes_filepath: str):
        # Configure factors
        factors = configure_scoring_factors_meta_from_csv(rating_model, factors_filepath)
        self.db.add_all(factors)
        self.db.flush()  # This ensures all factors have IDs

        # Configure attributes
        attributes = self.configure_attributes_scoring_from_csv(db,rating_model, attributes_filepath)
        self.db.add_all(attributes)
        
        # Commit all changes
        self.db.commit()

        return factors, attributes
# Usage example
if __name__ == "__main__":

    from main import create_engine_and_session, DB_NAME,init_db
    init_db(DB_NAME)
    _, db = create_engine_and_session(DB_NAME)
    rating_model = db.query(RatingModel).first()  # Or create a new one
        
    configure_rating_model_factors(db)
    # factors, attributes = app.configure_rating_model_from_csv(
    #         rating_model,
    #         "path_to_factors.csv",
    #         "path_to_attributes.csv"
    #     )
        
    # print(f"Configured {len(factors)} factors and {len(attributes)} attributes for the rating model.")
        # rating_model_app.check_quant_factors_presence_in_financial_template(
        #     rating_model)

        # modules = rating_model_app.organise_factors_in_modules(
        #     rating_model, FactorType.QUANTITATIVE)
        # print(modules)
