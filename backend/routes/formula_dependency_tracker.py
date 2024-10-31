# # dependencies.py
# from typing import Dict, Set, Optional
# from uuid import UUID
# from sqlalchemy.orm import Session
# import re

# def extract_dependencies(formula: Optional[str]) -> Set[str]:
#     """
#     Extract dependencies from a formula.
#     Returns a set of variable names used in the formula.
#     """
#     if not formula:
#         return set()
    
#     # Find all potential variable names (words) in the formula
#     tokens = re.findall(r'[a-zA-Z]\w*', formula)
    
#     # Filter out any Python keywords that might be in the formula
#     python_keywords = {'and', 'or', 'not', 'in', 'is'}
#     return {token for token in tokens if token not in python_keywords}

# def get_dependency_graph(db: Session, template_id: UUID) -> Dict[str, Set[str]]:
#     """
#     Build a dependency graph for all line items in a template.
    
#     Args:
#         db: Database session
#         template_id: Template UUID
        
#     Returns:
#         Dict mapping line item names to sets of their dependencies
    
#     Example:
#         For line items:
#         - revenue: "1000"
#         - costs: "500"
#         - profit: "revenue - costs"
#         - margin: "profit / revenue"
        
#         Returns:
#         {
#             'revenue': set(),
#             'costs': set(),
#             'profit': {'revenue', 'costs'},
#             'margin': {'profit', 'revenue'}
#         }
#     """
#     try:
#         # Get all line items for the template
#         line_items = db.query(LineItemMeta)\
#             .filter(LineItemMeta.template_id == template_id)\
#             .all()
        
#         # Initialize graph with empty dependencies for each line item
#         graph: Dict[str, Set[str]] = {item.name: set() for item in line_items}
#         valid_names = {item.name for item in line_items}
        
#         # Build dependencies for each line item with a formula
#         for item in line_items:
#             if item.formula:
#                 # Extract dependencies from formula
#                 dependencies = extract_dependencies(item.formula)
#                 # Only include valid line item names as dependencies
#                 graph[item.name] = {dep for dep in dependencies if dep in valid_names}
        
#         return graph
        
#     except Exception as e:
#         raise ValueError(f"Error building dependency graph: {str(e)}")

# # Optional: Add helper functions for graph operations

# def get_all_dependencies(graph: Dict[str, Set[str]], item_name: str) -> Set[str]:
#     """
#     Get all dependencies (direct and indirect) for a line item.
#     Uses DFS to traverse the dependency graph.
#     """
#     all_deps = set()
    
#     def dfs(node: str) -> None:
#         for dep in graph.get(node, set()):
#             if dep not in all_deps:
#                 all_deps.add(dep)
#                 dfs(dep)
    
#     dfs(item_name)
#     return all_deps

# def get_dependent_items(graph: Dict[str, Set[str]], item_name: str) -> Set[str]:
#     """
#     Get all items that depend on the given item (directly or indirectly).
#     """
#     dependents = set()
    
#     def dfs(node: str) -> None:
#         for other_item, deps in graph.items():
#             if node in deps and other_item not in dependents:
#                 dependents.add(other_item)
#                 dfs(other_item)
    
#     dfs(item_name)
#     return dependents

# def validate_dependency_addition(
#     graph: Dict[str, Set[str]],
#     item_name: str,
#     new_deps: Set[str]
# ) -> bool:
#     """
#     Check if adding new dependencies would create a cycle.
#     """
#     # Create a temporary copy of the graph
#     temp_graph = {k: set(v) for k, v in graph.items()}
#     temp_graph[item_name] = new_deps
    
#     # Check for cycles using DFS
#     visited = set()
#     path = set()
    
#     def has_cycle(node: str) -> bool:
#         visited.add(node)
#         path.add(node)
        
#         for dep in temp_graph.get(node, set()):
#             if dep not in visited:
#                 if has_cycle(dep):
#                     return True
#             elif dep in path:
#                 return True
        
#         path.remove(node)
#         return False
    
#     return any(has_cycle(node) for node in temp_graph if node not in visited)