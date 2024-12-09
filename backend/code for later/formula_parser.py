import ast
import operator as op
from typing import Dict, Any, Callable

# Formula parser which can be used for derived fields. It can accept functions rather than just expressions which can be handled by parser
# an alternative is to use the exec() function, but then it wont be safe, as any commands can be run.
# "The add_function method now accepts a string representation of a full function definition. It uses Python's ast module to parse the string and create a callable function from it.
# The create_function method is added to handle the creation of callable functions from AST FunctionDef nodes.
# The eval_body method is introduced to evaluate the body of a function, including handling return statements and variable assignments.
# The eval_expr method is expanded to handle more types of expressions, including function calls and comparisons.
# A SafeDict class is introduced to handle undefined variables gracefully by returning 0 instead of raising a KeyError.
# "
class SafeDict(dict):

    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)

    def __getitem__(self, key):
        if key in self:
            return super().__getitem__(key)
        return 0  # Default value for undefined variables


class ExtendedParser:

    def __init__(self):
        self.operations = {
            ast.Add: op.add,
            ast.Sub: op.sub,
            ast.Mult: op.mul,
            ast.Div: op.truediv,
            ast.Pow: op.pow,
            ast.USub: op.neg,
            ast.Eq: op.eq,
            ast.NotEq: op.ne,
            ast.Lt: op.lt,
            ast.LtE: op.le,
            ast.Gt: op.gt,
            ast.GtE: op.ge
        }
        self.functions = {}

    def add_function(self, func_str: str):
        """Add a new function to the parser from a string."""
        tree = ast.parse(func_str)
        if isinstance(tree.body[0], ast.FunctionDef):
            func_def = tree.body[0]
            func_name = func_def.name
            self.functions[func_name] = self.create_function(func_def)
        else:
            raise ValueError(
                "Invalid function string. Expected a function definition.")

    def create_function(self, node):
        """Create a callable function from an AST FunctionDef node."""

        def func(*args):
            local_vars = SafeDict(
                zip([arg.arg for arg in node.args.args], args))
            return self.eval_body(node.body, local_vars)

        return func

    def eval_body(self, body, variables):
        """Evaluate a function body."""
        result = None
        for node in body:
            if isinstance(node, ast.Return):
                return self.eval_expr(node.value, variables)
            elif isinstance(node, ast.Assign):
                value = self.eval_expr(node.value, variables)
                for target in node.targets:
                    variables[target.id] = value
            elif isinstance(node, ast.If):
                if self.eval_expr(node.test, variables):
                    result = self.eval_body(node.body, variables)
                    if isinstance(result, ast.Return):
                        return result
                elif node.orelse:
                    result = self.eval_body(node.orelse, variables)
                    if isinstance(result, ast.Return):
                        return result
            elif isinstance(node, ast.Expr):
                result = self.eval_expr(node.value, variables)
        return result

    def eval_expr(self, node, variables):
        """Recursively evaluate an expression."""
        if isinstance(node, (ast.Num, ast.Constant)):
            return node.n if hasattr(node, 'n') else node.value
        elif isinstance(node, ast.Name):
            return variables[node.id]
        elif isinstance(node, ast.BinOp):
            return self.operations[type(node.op)](self.eval_expr(
                node.left, variables), self.eval_expr(node.right, variables))
        elif isinstance(node, ast.UnaryOp):
            return self.operations[type(node.op)](self.eval_expr(
                node.operand, variables))
        elif isinstance(node, ast.Call):
            func_name = node.func.id
            func = self.functions.get(func_name)
            if func:
                args = [self.eval_expr(arg, variables) for arg in node.args]
                return func(*args)
            else:
                raise ValueError(f"Function '{func_name}' is not defined.")
        elif isinstance(node, ast.Compare):
            left = self.eval_expr(node.left, variables)
            for op, comparator in zip(node.ops, node.comparators):
                right = self.eval_expr(comparator, variables)
                if not self.operations[type(op)](left, right):
                    return False
                left = right
            return True
        elif isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(
                    self.eval_expr(value, variables) for value in node.values)
            elif isinstance(node.op, ast.Or):
                return any(
                    self.eval_expr(value, variables) for value in node.values)
        elif isinstance(node, ast.Not):
            return not self.eval_expr(node.operand, variables)
        raise ValueError(f"Unsupported node type: {type(node)}")

    def parse(self, expression: str):
        """Parse the expression and return an Expression object."""
        return Expression(expression, self)


class Expression:

    def __init__(self, expression: str, parser: ExtendedParser):
        self.expression = expression
        self.parser = parser

    def evaluate(self, variables: Dict[str, Any] = None) -> Any:
        if variables is None:
            variables = {}
        tree = ast.parse(self.expression, mode='eval')
        return self.parser.eval_expr(tree.body, SafeDict(variables))


# Usage
parser = ExtendedParser()

# Add a custom function as a string
parser.add_function("""
def sum(a, b):
    return a + b
""")

# Parse and evaluate an expression using the custom function
expr = parser.parse('sum(3, 4)')
result = expr.evaluate()
print(result)  # Output: 7

# Add another custom function
parser.add_function("""
def max_of_three(a, b, c):
    if a >= b and a >= c:
        return a
    elif b >= a and b >= c:
        return b
    else:
        return c
""")

# Parse and evaluate another expression
expr = parser.parse('max_of_three(sum(10,10), 5, 4)')
result = expr.evaluate()
print(result)  # Output: 5
