
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session
from typing import Tuple
from models.statement_models import Template
from models.statement_models import FinancialStatement, FinancialsPeriod, LineItemMeta, LineItemValue
from models.models import Customer
import csv
from typing import List, Dict
from config import create_engine_and_session
from main import TEMPLATE_DIRECTORY
from sqlalchemy.orm import joinedload
from sqlalchemy.dialects.postgresql import insert
import os
from schema import schema
from pydantic import ValidationError
import logging
# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
from py_expression_eval import Parser

import re
from schema import schema

class NullableFloat:
    def __init__(self, value: float = None):
        self.value = value
        self.valid = value is not None

class FsApp:
    def __init__(self, db: Session):
        self.db = db

    def generate_statement_data_for_customer(self, year_no_index: int,year:int, month:int, date:int, customer: Customer):
        template = self.db.query(Template).filter(Template.name == "FinTemplate").first()
        new_statement = FinancialStatement( financials_period_year=year, financials_period_month=month, financials_period_date=date, 
                                       customer=customer, template=template, is_dirty=True)

    # Find the preceding statement
        preceding_statement = self.db.query(FinancialStatement).filter(
            FinancialStatement.customer_id == customer.id,
            (FinancialStatement.financials_period_year < new_statement.financials_period_year) |
            ((FinancialStatement.financials_period_year == new_statement.financials_period_year) &
            (FinancialStatement.financials_period_month < new_statement.financials_period_month)) |
            ((FinancialStatement.financials_period_year == new_statement.financials_period_year) &
            (FinancialStatement.financials_period_month == new_statement.financials_period_month) &
            (FinancialStatement.financials_period_date < new_statement.financials_period_date))
        ).order_by(
            FinancialStatement.financials_period_year.desc(),
            FinancialStatement.financials_period_month.desc(),
            FinancialStatement.financials_period_date.desc()
        ).first()
        if preceding_statement:
            new_statement.preceding_statement_id = preceding_statement.id
            self.db.add(new_statement)
            self.db.flush()

        stmt_data = self.read_stmt_data(year_no_index)
        stmt_data_map = {item["name"]: item["value"] for item in stmt_data}

        all_fields = self.get_all_fields(template)
        all_field_values = []
        for field in all_fields:
            line_item = LineItemValue(financial_statement_id=new_statement.id, financial_statement=new_statement,
                                      line_item_meta_id=field.id, line_item_meta=field)
            line_item.value = stmt_data_map.get(field.name)
            all_field_values.append(line_item)

        self.db.add_all(all_field_values)
        self.db.flush()
        self.db.commit()
        lag_variables = self.get_lag_variables(statement=new_statement)    

        for l in lag_variables:
            # Get the current value of the lag variable
            new_value=self.get_lag_variable_value(statement=new_statement,lag_meta=l)
            self.update_or_create_lag_line_item_value(statement=new_statement,lag_meta=l,value=new_value)
        derived_fields = self.get_derived_fields(template)
        field_values_map = self.get_all_fields_values(new_statement)
        updated_derived_values_map = self.compute_derived_line_item_values(derived_fields, field_values_map)
        self.update_derived_field_values_in_db(new_statement, updated_derived_values_map)
        # self.update_financial_statement(statement)

        self.db.commit()
    def update_statement(self, statement_id: str, updated_values: List[schema.UpdatedValue]) -> Dict:
        statement = self.db.query(FinancialStatement).filter(FinancialStatement.id == statement_id).first()
        if not statement:
            raise ValueError(f"No statement found with id {statement_id}")

        template = statement.template

        # Update the values in the database
        for update in updated_values:
            line_item = self.db.query(LineItemValue).filter(
                LineItemValue.financial_statement_id == statement_id,
                LineItemValue.line_item_meta_id == update.template_financial_item_id
            ).first()
            if line_item:
                line_item.value = update.new_value

        self.db.flush()

        # Recalculate derived values
        derived_fields = self.get_derived_fields(template)
        field_values_map = self.get_all_fields_values(statement)
        updated_derived_values_map = self.compute_derived_line_item_values(derived_fields, field_values_map)
        self.update_derived_field_values_in_db(statement, updated_derived_values_map)

        # Commit changes
        self.db.commit()

        # Fetch updated data to return
        return

    def create_statement_data_for_customer(self, cif_number: str) -> Customer:
        customer = self.db.query(Customer).filter(Customer.cif_number == cif_number).first()
        # workflow_action = customer.workflow_action

        column_index_in_csv = 1
        for year in [2021, 2022, 2023]:
            period = self.db.query(FinancialsPeriod).filter(
                FinancialsPeriod.year == year,
                FinancialsPeriod.month == 12,
                FinancialsPeriod.date == 31
            ).first()
            month=12
            date=31 
            self.generate_statement_data_for_customer(column_index_in_csv,year,month, date, customer)
            column_index_in_csv += 1

        return customer

    @staticmethod
    def read_stmt_data(year_number: int) -> List[Dict]:
        stmt_data_path = os.path.join(TEMPLATE_DIRECTORY,"stmtData.csv")

        financial_items = []
        with open(stmt_data_path, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for record in reader:
                name = record[0].strip()
                try:
                    value = float(record[year_number].replace(',', ''))
                except ValueError:
                    value = 0.0
                financial_items.append({"name": name, "value": value})
        return financial_items

    def get_all_fields(self, template: Template) -> List[LineItemMeta]:
        return self.db.query(LineItemMeta).filter(LineItemMeta.template_id == template.id).all()

    def get_derived_fields(self, template: Template) -> List[LineItemMeta]:
        return self.db.query(LineItemMeta).filter(
            LineItemMeta.template_id == template.id,
            LineItemMeta.formula != None,LineItemMeta.formula != ''
        ).all()

    def get_all_fields_values(self, statement: FinancialStatement) -> Dict[str, NullableFloat]:

        values = (self.db.query(LineItemValue, LineItemMeta)
              .join(LineItemMeta)
              .filter(LineItemValue.financial_statement_id == statement.id)
              .order_by(LineItemMeta.order_no)
              .all())
        # we're using index access (item[0] and item[1]) instead of attribute access. This is because when you query multiple entities, SQLAlchemy returns each row as a tuple-like object where each item corresponds to one of the entities in the order they were queried.
        # item[0] corresponds to LineItemValue
        # item[1] corresponds to LineItemMeta
        return {item[1].name: NullableFloat(item[0].value) for item in values}

    # def get_lag_fields_values(self, statement: FinancialStatement) -> Dict[str, NullableFloat]:

    #     values = (self.db.query(LineItemValue, LineItemMeta)
    #           .join(LineItemMeta)
    #           .filter(LineItemValue.financial_statement_id == statement.id)
    #           .order_by(LineItemMeta.order_no)
    #           .all())
    #     # we're using index access (item[0] and item[1]) instead of attribute access. This is because when you query multiple entities, SQLAlchemy returns each row as a tuple-like object where each item corresponds to one of the entities in the order they were queried.
    #     # item[0] corresponds to LineItemValue
    #     # item[1] corresponds to LineItemMeta
    #     return {item[1].name: NullableFloat(item[0].value) for item in values}
    def get_statement_data(self, statement_ids: List[str]) -> Dict:
        statements = (self.db.query(FinancialStatement)
                      .options(joinedload(FinancialStatement.customer),
                               joinedload(FinancialStatement.template))
                      .filter(FinancialStatement.id.in_(statement_ids))
                      .order_by(FinancialStatement.financials_period_year,
                                FinancialStatement.financials_period_month,
                                FinancialStatement.financials_period_date)
                      .all())
        
        if not statements:
            raise ValueError(f"No statements found with the provided IDs")

        # Get line items for the first statement (assuming they're the same for all)
        first_statement = statements[0]
        line_items = (self.db.query(LineItemValue, LineItemMeta)
                      .join(LineItemMeta)
                      .filter(LineItemValue.financial_statement_id == first_statement.id)
                      .order_by(LineItemMeta.order_no)
                      .all())

        # Prepare the result structure
        spreading_line_items = []
        for i, (line_value, line_meta) in enumerate(line_items):
            try:
                item = schema.SpreadingLineItems(
                    statement_1=first_statement.id,
                    order_no=line_meta.order_no,
                    formula=line_meta.formula,
                    template_financial_line_item_name=line_meta.name,
                    template_id=first_statement.template_id,
                    template_financial_item_id=line_meta.id,
                    template_label=line_meta.label,
                    value_1=line_value.value
                )
                spreading_line_items.append(item)
            except ValidationError as e:
                logger.error(f"Validation error at index {i}:")
                logger.error(f"Line value: {line_value.__dict__}")
                logger.error(f"Line meta: {line_meta.__dict__}")
                logger.error(f"Error details: {e}")
                raise  # Remove this if you want to continue processing other items

        # Populate values for other statements
        for i, statement in enumerate(statements[1:], start=2):
            values = (self.db.query(LineItemValue.value)
                      .join(LineItemMeta)
                      .filter(LineItemValue.financial_statement_id == statement.id)
                      .order_by(LineItemMeta.order_no)
                      .all())
            
            if len(values) != len(spreading_line_items):
                raise ValueError(f"Mismatch in number of line items for statement {statement.id}")
            
            for j, value in enumerate(values):
                setattr(spreading_line_items[j], f"statement_{i}", statement.id)
                setattr(spreading_line_items[j], f"value_{i}", value[0])

        # Prepare the properties
        spreading_properties = schema.SpreadingStatementProperties(
            statement_type=first_statement.template.name,
            dates=[f"{s.financials_period_year}-{s.financials_period_month:02d}-{s.financials_period_date:02d}"
                   for s in statements]
        )
        dates_in_statement = [f"{s.financials_period_year}-{s.financials_period_month:02d}-{s.financials_period_date:02d}"
                              for s in statements]
        statement_type = first_statement.template.name.lower()

        return {
            "data": [item.dict() for item in spreading_line_items],  # Convert Pydantic models to dicts
            "statement_type": statement_type,
            "dates_in_statement": dates_in_statement
        }
    def get_statement_data_old(self, statement_ids: List[str]) -> Dict:
        statements = (self.db.query(FinancialStatement)
                      .options(joinedload(FinancialStatement.customer),
                               joinedload(FinancialStatement.template))
                      .filter(FinancialStatement.id.in_(statement_ids))
                      .order_by(FinancialStatement.financials_period_year,
                                FinancialStatement.financials_period_month,
                                FinancialStatement.financials_period_date)
                      .all())
        
        if not statements:
            raise ValueError(f"No statements found with the provided IDs")

        # Get line items for the first statement (assuming they're the same for all)
        first_statement = statements[0]
        line_items = (self.db.query(LineItemValue, LineItemMeta)
                      .join(LineItemMeta)
                      .filter(LineItemValue.financial_statement_id == first_statement.id)
                      .order_by(LineItemMeta.order_no)
                      .all())

        # Prepare the result structure
        spreading_line_items = []
        for i, (line_value, line_meta) in enumerate(line_items):
            try:
                item = schema.SpreadingLineItems(
                    # spreading_statement_properties_id=first_statement.id,
                    order_no=line_meta.order_no,
                    formula=line_meta.formula,
                    template_financial_line_item_name=line_meta.name,
                    template_id=first_statement.template_id,
                    template_financial_item_id=line_meta.id,
                    template_label=line_meta.label,
                    value_1=line_value.value
                )
                spreading_line_items.append(item)
            except ValidationError as e:
                logger.error(f"Validation error at index {i}:")
                logger.error(f"Line value: {line_value.__dict__}")
                logger.error(f"Line meta: {line_meta.__dict__}")
                logger.error(f"Error details: {e}")
            # Optionally, you can re-raise the error or continue to the next iteration
                raise  # Remove this if you want to continue processing other items

        # Populate values for other statements
        for i, statement in enumerate(statements[1:], start=2):
            values = (self.db.query(LineItemValue.value)
                      .join(LineItemMeta)
                      .filter(LineItemValue.financial_statement_id == statement.id)
                      .order_by(LineItemMeta.order_no)
                      .all())
            
            if len(values) != len(spreading_line_items):
                raise ValueError(f"Mismatch in number of line items for statement {statement.id}")
            
            for j, value in enumerate(values):
                setattr(spreading_line_items[j], f"value_{i}", value[0])

        # Prepare the properties
        spreading_properties = schema.SpreadingStatementProperties(
            statement_type=first_statement.template.name,
            dates=[f"{s.financials_period_year}-{s.financials_period_month:02d}-{s.financials_period_date:02d}"
                   for s in statements]
        )
        dates_in_statement = [f"{s.financials_period_year}-{s.financials_period_month:02d}-{s.financials_period_date:02d}"
                              for s in statements]
        statement_type = first_statement.template.name.lower()  # Assuming 'pnl' is lowercase in the template name

        return {
            "data": spreading_line_items,
            "statement_type": statement_type,
            "dates_in_statement": dates_in_statement
        }
        
    def compute_derived_line_item_values(
        self,
        derived_fields: List[LineItemMeta],
        field_values_map: Dict[str, NullableFloat]
    ) -> Tuple[Dict[str, NullableFloat], Dict[str, NullableFloat]]:
        updated_derived_fields = {}
        env = {}

        # Populate the environment with valid float values
        for key, value in field_values_map.items():
            if value.valid:
                env[key] = value.value

        parser = Parser()

        for derived_field in derived_fields:
            if derived_field.lag_months > 0:
                updated_derived_fields[derived_field.name] = field_values_map[derived_field.name]
                continue  # Skip lag variables that have already been updated

            try:
                # Parse and evaluate the formula
                expression = parser.parse(derived_field.formula)
                result=expression.evaluate(env)

                # Convert the result to a float
                float_value = float(result)

                updated_derived_fields[derived_field.name] = NullableFloat(float_value)
                env[derived_field.name] = float_value
                field_values_map[derived_field.name] = NullableFloat(float_value)
            except Exception as e:
                print(f"Error in {derived_field.name}: {str(e)}")
                updated_derived_fields[derived_field.name] = NullableFloat()

        return updated_derived_fields



    def update_derived_field_values_in_db(self, statement: FinancialStatement, derived_map: Dict[str, NullableFloat]):
        # Get all derived fields for this statement's template
        derived_fields = self.get_derived_fields(statement.template)
        
        # Create a mapping of line item meta names to their IDs
        name_to_id_map = {field.name: field.id for field in derived_fields}
        
        for name, nullable_value in derived_map.items():
            if name not in name_to_id_map:
                print(f"Warning: No LineItemMeta found for name: {name}")
                continue

            # Using SQLAlchemy's insert ... on conflict do update
            insert_stmt = insert(LineItemValue).values(
                financial_statement_id=statement.id,
                line_item_meta_id=name_to_id_map[name],
                value=nullable_value.value if nullable_value.valid else None
            )
            
            do_update_stmt = insert_stmt.on_conflict_do_update(
                constraint='uix_financial_statement_line_item',  # Use the correct constraint name
                set_=dict(value=insert_stmt.excluded.value)
            )

            self.db.execute(do_update_stmt)

        self.db.commit()
    def update_financial_statement(self, statement: FinancialStatement):
        # This method needs to be implemented based on your specific update logic
        pass
    
    def get_lag_variables(self, statement: FinancialStatement):
            lag_variables = {}

        # Get all LineItemMeta with lag_period > 0 for the statement's template
            lag_metas = self.db.query(LineItemMeta).filter(
                LineItemMeta.template_id == statement.template_id,
                LineItemMeta.lag_months > 0
            ).all()

            return lag_metas
    
            
    def remove_lag_suffix(self,name: str) -> str:
        return re.sub(r'_lag\d+$', '', name)

    def process_and_update_lag_variables(self, statement: FinancialStatement):
        lag_metas = self.get_lag_variables(statement)
        
        for lag_meta in lag_metas:
            lag_value = self.get_lag_variable_value(statement, lag_meta)
            if lag_value is not None:
                self.update_or_create_line_item_value(statement, lag_meta, lag_value)
    def get_base_line_item_meta_id(self, lag_meta: LineItemMeta) :
            base_name = self.remove_lag_suffix(lag_meta.name)
            base_meta = self.db.query(LineItemMeta).filter(
                LineItemMeta.template_id == lag_meta.template_id,
                LineItemMeta.name == base_name,
                LineItemMeta.lag_months == 0
            ).first()
            return base_meta.id if base_meta else None
    def get_lag_variable_value(self, statement: FinancialStatement, lag_meta: LineItemMeta) -> float:

        preceding_statement_id = statement.preceding_statement_id
        
        if preceding_statement_id:
            base_meta_id = self.get_base_line_item_meta_id(lag_meta)
            if base_meta_id:
                line_item_value = self.db.query(LineItemValue).filter(
                    LineItemValue.financial_statement_id == preceding_statement_id,
                    LineItemValue.line_item_meta_id == base_meta_id
                ).first()
                if line_item_value:
                    return line_item_value.value

        return None

    def update_or_create_lag_line_item_value(self, statement: FinancialStatement, lag_meta: LineItemMeta, value: float):
        line_item_value = self.db.query(LineItemValue).filter(
            LineItemValue.financial_statement_id == statement.id,
            LineItemValue.line_item_meta_id == lag_meta.id
        ).first()
        if line_item_value:
            line_item_value.value = value
        else:
            line_item_value = LineItemValue(
                financial_statement_id=statement.id,
                line_item_meta_id=lag_meta.id,
                value=value
            )
            self.db.add(line_item_value)
        self.db.commit()
    def update_field_and_derived_values(self, statement_id: str, field_name: str, new_value: float):
        statement = self.db.query(FinancialStatement).filter(FinancialStatement.id == statement_id).first()
        if not statement:
            raise ValueError(f"No statement found with id {statement_id}")

        # Update the specified field
        line_item = self.db.query(LineItemValue).join(LineItemMeta).filter(
            LineItemValue.financial_statement_id == statement_id,
            LineItemMeta.name == field_name
        ).first()

        if not line_item:
            raise ValueError(f"No field found with name {field_name} for statement {statement_id}")

        line_item.value = new_value
        self.db.flush()

        lag_variables = self.get_lag_variables(statement=statement)    

        for l in lag_variables:
            # Get the current value of the lag variable
            new_value=self.get_lag_variable_value(statement=statement,lag_meta=l)
            # if new_value:
            self.update_or_create_lag_line_item_value(statement=statement,lag_meta=l,value=new_value)

        # Get all fields and their current values
        field_values_map = self.get_all_fields_values(statement)
        # Get derived fields
        derived_fields = self.get_derived_fields(statement.template)

        # Recompute derived fields
        updated_derived_values_map = self.compute_derived_line_item_values(derived_fields, field_values_map)

        # Update derived fields in the database
        self.update_derived_field_values_in_db(statement, updated_derived_values_map)

        # Mark the statement as dirty
        statement.is_dirty = True

        self.db.commit()

        return updated_derived_values_map

    def find_best_preceding_statement(self, customer_id: UUID, statement_date: datetime = None):
        """
        Find the best preceding statement based on hierarchy:
        1. If statement_date provided: Get statements before that date
        If no statement_date: Get all statements
        2. Preference for Audited over Unaudited
        3. Preference for Actuals over Projections
        """
        # Base query
        query = self.db.query(FinancialStatement).filter(
            FinancialStatement.customer_id == customer_id
        )

        # Add date filtering only if statement_date is provided
        if statement_date:
            query = query.filter(
                ((FinancialStatement.financials_period_year < statement_date.year) |
                ((FinancialStatement.financials_period_year == statement_date.year) &
                (FinancialStatement.financials_period_month < statement_date.month)) |
                ((FinancialStatement.financials_period_year == statement_date.year) &
                (FinancialStatement.financials_period_month == statement_date.month) &
                (FinancialStatement.financials_period_date < statement_date.day)))
            )

        # Get all potential statements ordered by date
        previous_statements = query.order_by(
            FinancialStatement.financials_period_year.desc(),
            FinancialStatement.financials_period_month.desc(),
            FinancialStatement.financials_period_date.desc()
        ).all()

        if not previous_statements:
            return None

        # Group statements by date
        statements_by_date = {}
        for stmt in previous_statements:
            date_key = (stmt.financials_period_year, 
                    stmt.financials_period_month, 
                    stmt.financials_period_date)
            if date_key not in statements_by_date:
                statements_by_date[date_key] = []
            statements_by_date[date_key].append(stmt)

        # Get the most recent date's statements
        most_recent_date = max(statements_by_date.keys())
        candidates = statements_by_date[most_recent_date]

        # Apply preference hierarchy
        # First preference: Audited Actuals
        for stmt in candidates:
            if stmt.audit_type == 'Audited' and stmt.actuals:
                return stmt

        # Second preference: Unaudited Actuals
        for stmt in candidates:
            if stmt.audit_type == 'Unaudited' and stmt.actuals:
                return stmt

        # Third preference: Audited Projections
        for stmt in candidates:
            if stmt.audit_type == 'Audited' and stmt.projections:
                return stmt

        # Last preference: Unaudited Projections
        for stmt in candidates:
            if stmt.audit_type == 'Unaudited' and stmt.projections:
                return stmt

        # If somehow none matched our criteria, return the first one
        return candidates[0]

    def get_available_preceding_statements(self, customer_id: UUID, statement_date: datetime = None):
        """
        Get all available preceding statements, ordered by preference and date.
        Returns a list of tuples (statement, is_recommended)
        """
        query = self.db.query(FinancialStatement).filter(
            FinancialStatement.customer_id == customer_id
        )

        if statement_date:
            query = query.filter(
                ((FinancialStatement.financials_period_year < statement_date.year) |
                ((FinancialStatement.financials_period_year == statement_date.year) &
                (FinancialStatement.financials_period_month < statement_date.month)) |
                ((FinancialStatement.financials_period_year == statement_date.year) &
                (FinancialStatement.financials_period_month == statement_date.month) &
                (FinancialStatement.financials_period_date < statement_date.day)))
            )

        statements = query.order_by(
            FinancialStatement.financials_period_year.desc(),
            FinancialStatement.financials_period_month.desc(),
            FinancialStatement.financials_period_date.desc()
        ).all()

        # Find the recommended statement
        recommended_stmt = self.find_best_preceding_statement(customer_id, statement_date)
        
        # Add a display name and recommendation flag to each statement
        result = []
        for stmt in statements:
            display_name = (
                f"{stmt.audit_type} "
                f"{'Actuals' if stmt.actuals else 'Projections'} "
                f"{stmt.financials_period_year}-{stmt.financials_period_month:02d}-{stmt.financials_period_date:02d}"
            )
            is_recommended = recommended_stmt and stmt.id == recommended_stmt.id
            result.append({
                'statement': stmt,
                'display_name': display_name,
                'is_recommended': is_recommended
            })

        return result
# Usage


if __name__ == "__main__":
    from config import DB_NAME
    _, db = create_engine_and_session(DB_NAME)
    app = FsApp(db)
    customer = app.create_statement_data_for_customer("CIF-123456")
    print(f"Created statement data for customer: {customer.customer_name}")