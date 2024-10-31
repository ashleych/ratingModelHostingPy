
# # formula_validator.py
# from typing import Dict, Set, Tuple, List, Optional, Union
# from uuid import UUID
# from sqlalchemy.orm import Session
# import re
# from dataclasses import dataclass
# from enum import Enum, auto
# from models.models import LineItemMeta


# class ValidationErrorType(Enum):
#     EMPTY = auto()
#     SINGLE_OPERATOR = auto()
#     INVALID_TOKEN = auto()
#     INVALID_LINE_ITEM = auto()
#     CIRCULAR_REFERENCE = auto()
#     SYNTAX_ERROR = auto()
#     DATABASE_ERROR = auto()


# @dataclass
# class ValidationResult:
#     is_valid: bool
#     error_type: Optional[ValidationErrorType] = None
#     error_message: str = ""
#     invalid_token: str = ""


# class FormulaValidator:
#     def __init__(self):
#         self.valid_operators = {'+', '-', '*', '/', '(', ')'}

#     def _tokenize_formula(self, formula: str) -> List[str]:
#         """Split formula into tokens and strip whitespace"""
#         tokens = re.findall(r'[\w_]+|[+\-*/()]', formula)
#         return [t.strip() for t in tokens]

#     def _is_valid_variable_name(self, token: str) -> bool:
#         """Check if token is a valid variable name"""
#         return bool(re.match(r'^[a-zA-Z]\w*$', token))

#     def validate_formula(
#         self,
#         formula: str,
#         valid_names: Set[str],
#         line_item_name: Optional[str] = None,
#         dependency_graph: Optional[Dict[str, Set[str]]] = None
#     ) -> ValidationResult:
#         """
#         Validate a formula against a set of rules and dependencies.

#         Args:
#             formula: The formula to validate
#             valid_names: Set of valid line item names
#             line_item_name: Name of the line item being edited (for circular ref check)
#             dependency_graph: Current dependency graph (for circular ref check)

#         Returns:
#             ValidationResult object containing validation status and any error details
#         """
#         try:
#             # Check for empty formula
#             if not formula.strip():
#                 return ValidationResult(
#                     is_valid=False,
#                     error_type=ValidationErrorType.EMPTY,
#                     error_message="Formula is empty. This line item will not be calculated."
#                 )

#             # Tokenize formula
#             tokens_stripped = self._tokenize_formula(formula)

#             # Check for single operator
#             if len(tokens_stripped) == 1 and tokens_stripped[0] in self.valid_operators:
#                 return ValidationResult(
#                     is_valid=False,
#                     error_type=ValidationErrorType.SINGLE_OPERATOR,
#                     error_message="Cannot use a single operator alone. Formula must include line item names."
#                 )

#             # Track dependencies found in formula
#             formula_deps = set()

#             # Validate each token
#             for token in tokens_stripped:
#                 # Skip operators
#                 if token in self.valid_operators:
#                     continue

#                 # Validate variable name
#                 if self._is_valid_variable_name(token):
#                     if token not in valid_names:
#                         return ValidationResult(
#                             is_valid=False,
#                             error_type=ValidationErrorType.INVALID_LINE_ITEM,
#                             error_message=f"Invalid line item name: '{token}'",
#                             invalid_token=token
#                         )
#                     formula_deps.add(token)
#                 else:
#                     return ValidationResult(
#                         is_valid=False,
#                         error_type=ValidationErrorType.INVALID_TOKEN,
#                         error_message=f"Invalid token: '{token}'. Line item names must start with a letter and can only contain letters, numbers, and underscores.",
#                         invalid_token=token
#                     )

#             # Check for circular references if dependency information is provided
#             if dependency_graph is not None and line_item_name is not None:
#                 # Temporarily add new dependencies to graph
#                 temp_graph = dict(dependency_graph)
#                 temp_graph[line_item_name] = formula_deps

#                 if self._detect_cycle(temp_graph, line_item_name):
#                     return ValidationResult(
#                         is_valid=False,
#                         error_type=ValidationErrorType.CIRCULAR_REFERENCE,
#                         error_message="Formula creates a circular reference."
#                     )

#             # If we got here, formula is valid
#             return ValidationResult(is_valid=True)

#         except Exception as e:
#             return ValidationResult(
#                 is_valid=False,
#                 error_type=ValidationErrorType.SYNTAX_ERROR,
#                 error_message=f"Error validating formula: {str(e)}"
#             )

#     def _detect_cycle(self, graph: Dict[str, Set[str]], start: str) -> bool:
#         """Detect cycles in the dependency graph using DFS"""
#         visited = set()
#         path = set()

#         def dfs(node: str) -> bool:
#             visited.add(node)
#             path.add(node)

#             for neighbor in graph.get(node, set()):
#                 if neighbor not in visited:
#                     if dfs(neighbor):
#                         return True
#                 elif neighbor in path:
#                     return True

#             path.remove(node)
#             return False

#         return dfs(start)

# def get_valid_line_items(db: Session, template_id: UUID) :
#     """Get all valid line item names for a template"""
#     try:
#         valid_items = db.query(LineItemMeta)\
#             .filter(LineItemMeta.template_id == template_id)\
#             .all()
#         return [item.name for item in valid_items]
#     except Exception as e:
#         raise ValueError(f"Error fetching line items: {str(e)}")
