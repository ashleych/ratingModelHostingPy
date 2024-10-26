import pytest
from routes.fs_line_item_routes import validate_syntax

@pytest.mark.parametrize(
    "formula,valid_names,current_item,expected_valid,expected_message",
    [
        # Valid cases
        (
            "revenue + expenses",
            {'revenue', 'expenses'},
            'profit',
            True,
            ""
        ),
        (
            "revenue - expenses",
            {'revenue', 'expenses'},
            'profit',
            True,
            ""
        ),
        (
            "revenue * tax_rate",
            {'revenue', 'tax_rate'},
            'tax',
            True,
            ""
        ),
        (
            "(revenue - expenses) * tax_rate",
            {'revenue', 'expenses', 'tax_rate'},
            'tax',
            True,
            ""
        ),
        
        # Invalid operator cases
        (
            "+revenue + expenses",
            {'revenue', 'expenses'},
            'profit',
            False,
            "Invalid formula: Cannot start with an operator"
        ),
        (
            "revenue + expenses +",
            {'revenue', 'expenses'},
            'profit',
            False,
            "Invalid formula: Cannot end with an operator"
        ),
        (
            "revenue ++ expenses",
            {'revenue', 'expenses'},
            'profit',
            False,
            "Invalid formula: Cannot have consecutive operators '++"
        ),
        
        # Invalid parentheses cases
        (
            "(revenue + expenses",
            {'revenue', 'expenses'},
            'profit',
            False,
            "Invalid formula: Mismatched parentheses - missing closing parenthesis"
        ),
        (
            "revenue + expenses)",
            {'revenue', 'expenses'},
            'profit',
            False,
            "Invalid formula: Mismatched parentheses - unexpected closing parenthesis"
        ),
        (
            "((revenue + expenses)",
            {'revenue', 'expenses'},
            'profit',
            False,
            "Invalid formula: Mismatched parentheses - missing closing parenthesis"
        ),
        
        # Invalid variable name cases
        (
            "revenue + 123invalid",
            {'revenue'},
            'profit',
            False,
            "Invalid token: '123invalid'. Line item names must start with a letter and can only contain letters, numbers, and underscores"
        ),
        (
            "revenue + !invalid",
            {'revenue'},
            'profit',
            False,
            "Invalid token: '!invalid'. Line item names must start with a letter and can only contain letters, numbers, and underscores"
        ),
        
        # Missing reference cases
        (
            "revenue + nonexistent",
            {'revenue'},
            'profit',
            False,
            "Invalid line item name: 'nonexistent'"
        ),
        
        # Self reference cases
        (
            "revenue + profit",
            {'revenue', 'profit'},
            'profit',
            False,
            "Invalid formula: Cannot reference the line item itself in its formula"
        ),
        (
            "profit",
            {'profit'},
            'profit',
            False,
            "Invalid formula: Cannot reference the line item itself in its formula"
        ),
        
        # Empty formula cases
        (
            "",
            {'revenue'},
            'profit',
            False,
            "Formula is empty. This line item will not be calculated."
        ),
        (
            "   ",
            {'revenue'},
            'profit',
            False,
            "Formula is empty. This line item will not be calculated."
        ),
        
        # Single operator cases
        (
            "+",
            {'revenue'},
            'profit',
            False,
            "Invalid formula: Cannot use a single operator alone. Formula must include line item names."
        ),
        
        # Complex valid cases
        (
            "((revenue + other_revenue) - (direct_costs + indirect_costs)) * (1 - tax_rate)",
            {'revenue', 'other_revenue', 'direct_costs', 'indirect_costs', 'tax_rate'},
            'net_profit',
            True,
            ""
        ),
        (
            "cost_a + cost_b + cost_c + cost_d",
            {'cost_a', 'cost_b', 'cost_c', 'cost_d'},
            'total_cost',
            True,
            ""
        )
    ]
)
def test_syntax_validation(formula, valid_names, current_item, expected_valid, expected_message):
    is_valid, message = validate_syntax(formula, valid_names, current_item)
    assert is_valid == expected_valid
    assert message == expected_message

def test_whitespace_handling():
    """Test that the function handles different whitespace patterns correctly"""
    valid_names = {'revenue', 'expenses'}
    test_cases = [
        "revenue+expenses",
        "revenue   +   expenses",
        " revenue + expenses ",
        "\trevenue\t+\texpenses\t",
        "\nrevenue +\nexpenses\n"
    ]
    for formula in test_cases:
        is_valid, message = validate_syntax(formula, valid_names, 'profit')
        assert is_valid == True, f"Failed for formula: '{formula}'"
        assert message == ""

def test_case_sensitivity():
    """Test that the function is case sensitive"""
    valid_names = {'Revenue', 'Expenses'}
    is_valid, message = validate_syntax("revenue + expenses", valid_names, 'Profit')
    assert is_valid == False
    assert "Invalid line item name: 'revenue'" in message

def test_special_characters():
    """Test handling of special characters in formulas"""
    valid_names = {'revenue', 'expenses'}
    test_cases = [
        ("revenue @ expenses", False),
        ("revenue & expenses", False),
        ("revenue % expenses", False),
        ("revenue $ expenses", False)
    ]
    for formula, expected_valid in test_cases:
        is_valid, message = validate_syntax(formula, valid_names, 'profit')
        assert is_valid == expected_valid, f"Failed for formula: '{formula}'"

def test_numeric_literals():
    """Test that the function rejects numeric literals"""
    valid_names = {'revenue'}
    is_valid, message = validate_syntax("revenue + 100", {'revenue'}, 'profit')
    assert is_valid == False
    assert "Invalid token: '100'" in message

def test_empty_valid_names():
    """Test behavior when valid_names set is empty"""
    is_valid, message = validate_syntax("a + b", set(), 'result')
    assert is_valid == False
    assert "Invalid line item name: " in message

def test_none_values():
    """Test handling of None values"""
    with pytest.raises(AttributeError):
        validate_syntax(None, {'revenue'}, 'profit')
    
    with pytest.raises(TypeError):
        validate_syntax("revenue + expenses", None, 'profit')
    
    with pytest.raises(TypeError):
        validate_syntax("revenue + expenses", {'revenue', 'expenses'}, None)