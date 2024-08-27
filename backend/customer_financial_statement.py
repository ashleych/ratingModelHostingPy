
from sqlalchemy.orm import Session
from typing import Tuple
from models.models import Customer, WorkflowAction, FinancialsPeriod, Template, FinancialStatement, LineItemMeta, LineItemValue
import csv
from typing import List, Dict
from main import create_engine_and_session
from main import TEMPLATE_DIRECTORY
from sqlalchemy.orm import joinedload
from sqlalchemy.dialects.postgresql import insert
import os

from py_expression_eval import Parser
class NullableFloat:
    def __init__(self, value: float = None):
        self.value = value
        self.valid = value is not None
class FsApp:
    def __init__(self, db_name: str):
        self.db_name = db_name
        self.engine, self.session = create_engine_and_session(db_name)

    def generate_statement_data_for_customer(self, year_no: int, period: FinancialsPeriod, 
                                             workflow_action: WorkflowAction, customer: Customer):
        template = self.session.query(Template).filter(Template.name == "FinTemplate").first()
        statement = FinancialStatement(financials_period=period, workflow_action=workflow_action, 
                                       customer=customer, template=template, is_dirty=True)
        self.session.add(statement)
        self.session.flush()

        stmt_data = self.read_stmt_data(year_no)
        stmt_data_map = {item["name"]: item["value"] for item in stmt_data}

        all_fields = self.get_all_fields(template)
        all_field_values = []
        for field in all_fields:
            line_item = LineItemValue(financial_statement_id=statement.id, financial_statement=statement,
                                      line_item_meta_id=field.id, line_item_meta=field)
            line_item.value = stmt_data_map.get(field.name)
            all_field_values.append(line_item)

        self.session.add_all(all_field_values)
        self.session.flush()

        derived_fields = self.get_derived_fields(template)
        field_values_map = self.get_all_fields_values(statement)
        updated_derived_values_map = self.compute_derived_line_item_values(derived_fields, field_values_map)
        self.update_derived_field_values_in_db(statement, updated_derived_values_map)
        # self.update_financial_statement(statement)

        self.session.commit()

    def create_statement_data_for_customer(self, cif_number: str) -> Customer:
        customer = self.session.query(Customer).filter(Customer.cif_number == cif_number).first()
        workflow_action = customer.workflow_action

        column_index_in_csv = 1
        for year in [2021, 2022, 2023]:
            period = self.session.query(FinancialsPeriod).filter(
                FinancialsPeriod.year == year,
                FinancialsPeriod.month == 12,
                FinancialsPeriod.date == 31
            ).first()
            self.generate_statement_data_for_customer(column_index_in_csv, period, workflow_action, customer)
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
        return self.session.query(LineItemMeta).filter(LineItemMeta.template_id == template.id).all()

    def get_derived_fields(self, template: Template) -> List[LineItemMeta]:
        return self.session.query(LineItemMeta).filter(
            LineItemMeta.template_id == template.id,
            LineItemMeta.formula != None,LineItemMeta.formula != ''
        ).all()

    # def get_all_fields_values(self, statement: FinancialStatement) -> Dict[str, float]:
    #     values = self.session.query(LineItemValue).filter(LineItemValue.financial_statement_id == statement.id).all()
    #     return {value.line_item_meta.name: value.value for value in values}
    # def get_all_fields_values(self, statement: FinancialStatement) -> Dict[str, NullableFloat]:
    #     values = self.session.query(LineItemValue).filter(LineItemValue.financial_statement_id == statement.id).all()

    #     return {value.line_item_meta_name: NullableFloat(value.value) for value in values}

    def get_all_fields_values(self, statement: FinancialStatement) -> Dict[str, NullableFloat]:
        values = self.session.query(LineItemValue).options(joinedload(LineItemValue.line_item_meta)).filter(
            LineItemValue.financial_statement_id == statement.id
        ).all()
        return {value.line_item_meta.name: NullableFloat(value.value) for value in values}

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
        parser.parse('2 * x').evaluate({'x': 7})

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


    # def update_derived_field_values_in_db(self, statement: FinancialStatement, updated_values: Dict[str, float]):
    #     for name, value in updated_values.items():
    #         line_item = self.session.query(LineItemValue).join(LineItemMeta).filter(
    #             LineItemValue.financial_statement_id == statement.id,
    #             LineItemMeta.name == name
    #         ).first()
    #         if line_item:
    #             line_item.value = value
    # def update_derived_field_values_in_db(self, statement: FinancialStatement, derived_map: Dict[str, NullableFloat]):
    #     line_item_input = LineItemValue()
        
    #     for key, nullable_value in derived_map.items():
    #         line_item_input.financial_statement_id = statement.id
    #         line_item_input.line_item_meta_id = UUID(key)  # Assuming key is a string representation of UUID
    #         line_item_input.value = nullable_value.value if nullable_value.valid else None

    #         # Using SQLAlchemy's insert ... on conflict do update
    #         insert_stmt = insert(LineItemValue).values(
    #             financial_statement_id=line_item_input.financial_statement_id,
    #             line_item_meta_id=line_item_input.line_item_meta_id,
    #             value=line_item_input.value
    #         )
            
    #         do_update_stmt = insert_stmt.on_conflict_do_update(
    #             constraint='lineitemvalue_pkey',  # Assuming this is your primary key constraint name
    #             set_=dict(value=line_item_input.value)
    #         )

    #         self.session.execute(do_update_stmt)

    #     self.session.commit()
    def update_derived_field_values_in_db(self, statement: FinancialStatement, derived_map: Dict[str, NullableFloat]):
        # Get all derived fields for this statement's template
        derived_fields = self.get_derived_fields(statement.template)
        
        # Create a mapping of line item meta names to their IDs
        name_to_id_map = {field.name: field.id for field in derived_fields}

        line_item_input = LineItemValue()
        
        for name, nullable_value in derived_map.items():
            if name not in name_to_id_map:
                print(f"Warning: No LineItemMeta found for name: {name}")
                continue

            line_item_input.financial_statement_id = statement.id
            line_item_input.line_item_meta_id = name_to_id_map[name]
            line_item_input.value = nullable_value.value if nullable_value.valid else None

            # Using SQLAlchemy's insert ... on conflict do update
            insert_stmt = insert(LineItemValue).values(
                financial_statement_id=line_item_input.financial_statement_id,
                line_item_meta_id=line_item_input.line_item_meta_id,
                value=line_item_input.value
            )
            
            do_update_stmt = insert_stmt.on_conflict_do_update(
                constraint='lineitemvalue_pkey',  # Assuming this is your primary key constraint name
                set_=dict(value=line_item_input.value)
            )

            self.session.execute(do_update_stmt)

        self.session.commit()

    def update_financial_statement(self, statement: FinancialStatement):
        # This method needs to be implemented based on your specific update logic
        pass

# Usage
if __name__ == "__main__":
    from main import DB_NAME
    app = FsApp(DB_NAME)
    customer = app.create_statement_data_for_customer("CIF-123456")
    print(f"Created statement data for customer: {customer.customer_name}")