
import pytest
from routes.fs_line_item_routes import check_circular_reference

@pytest.mark.parametrize(
    "formulas,item_name,formula,expected_valid,expected_path",
    [
        # Simple valid cases
        (
            {'a': '100', 'b': '200'},
            'new_item',
            'a + b',
            True,
            []
        ),
        # Direct circular reference
        (
            {'a': 'b', 'b': '200'},
            'b',
            'a',
            False,
            ['a', 'b']  # path: b -> a -> b
        ),
        # Indirect circular reference
        (
            {'a': 'b', 'b': 'c', 'c': 'd'},
            'd',
            'a',
            False,
            ['a', 'b', 'c', 'd']  # path: d -> a -> b -> c -> d
        ),
        # Complex valid case
        (
            {
                'revenue': '1000',
                'costs': '500',
                'profit': 'revenue - costs',
                'margin': 'profit / revenue'
            },
            'new_metric',
            'margin + revenue',
            True,
            []
        ),
        # Complex circular case
        (
            {
                'revenue': '1000',
                'costs': '500',
                'profit': 'revenue - costs',
                'margin': 'profit / revenue'
            },
            'revenue',
            'margin * 2',
            False,
            ['margin', 'profit', 'revenue']  # path: revenue -> margin -> profit -> revenue
        ),
        # Empty formula
        (
            {'a': '100', 'b': '200'},
            'new_item',
            '',
            True,
            []
        ),
        # Formula with no dependencies
        (
            {'a': '100', 'b': '200'},
            'new_item',
            '500',
            True,
            []
        ),
        # Long dependency chain but no circle
        (
            {
                'a': '100',
                'b': 'a',
                'c': 'b',
                'd': 'c',
                'e': 'd'
            },
            'f',
            'e',
            True,
            []
        ),
    ],
    ids=[
        "simple_valid_case",
        "direct_circular_reference",
        "indirect_circular_reference",
        "complex_valid_case",
        "complex_circular_case",
        "empty_formula",
        "formula_no_dependencies",
        "long_chain_no_circle"
    ]
)
def test_circular_reference_checker(formulas, item_name, formula, expected_valid, expected_path):
    is_valid, path = check_circular_reference(formulas, item_name, formula)
    assert is_valid == expected_valid
    assert path == expected_path

# @pytest.mark.parametrize(
#     "formulas,item_name,formula,expected_valid,expected_path,test_id",
#     [
#         # Simple valid cases
#         (
#             {'a': '100', 'b': '200'},
#             'new_item',
#             'a + b',
#             True,
#             [],
#             "simple_valid_formulas_with_two_variables"
#         ),
#         # Direct circular reference
#         (
#             {'a': 'b', 'b': '200'},
#             'b',
#             'a',
#             False,
#             ['a', 'b'],
#             "direct_circular_reference_through_two_variables"
#         ),
#         # Indirect circular reference
#         (
#             {'a': 'b', 'b': 'c', 'c': 'd'},
#             'd',
#             'a',
#             False,
#             ['a', 'b', 'c', 'd'],
#             "indirect_circular_reference_through_four_variables"
#         ),
#         # Complex valid case
#         (
#             {
#                 'revenue': '1000',
#                 'costs': '500',
#                 'profit': 'revenue - costs',
#                 'margin': 'profit / revenue'
#             },
#             'new_metric',
#             'margin + revenue',
#             True,
#             [],
#             "valid_financial_calculations_with_margin"
#         ),
#         # Complex circular case
#         (
#             {
#                 'revenue': '1000',
#                 'costs': '500',
#                 'profit': 'revenue - costs',
#                 'margin': 'profit / revenue'
#             },
#             'revenue',
#             'margin * 2',
#             False,
#             ['margin', 'profit', 'revenue'],
#             "circular_reference_in_financial_calculations"
#         ),
#         # Empty formula
#         (
#             {'a': '100', 'b': '200'},
#             'new_item',
#             '',
#             True,
#             [],
#             "empty_formula_should_be_valid"
#         ),
#         # Formula with no dependencies
#         (
#             {'a': '100', 'b': '200'},
#             'new_item',
#             '500',
#             True,
#             [],
#             "constant_formula_with_no_dependencies"
#         ),
#         # Long dependency chain but no circle
#         (
#             {
#                 'a': '100',
#                 'b': 'a',
#                 'c': 'b',
#                 'd': 'c',
#                 'e': 'd'
#             },
#             'f',
#             'e',
#             True,
#             [],
#             "long_chain_of_dependencies_without_circle"
#         ),
#     ],
#     ids=lambda x: x[-1] if isinstance(x, tuple) else None  # Use the last element (test_id) for the test name
# )
# def test_circular_reference_checker(formulas, item_name, formula, expected_valid, expected_path, test_id):
#     is_valid, path = check_circular_reference(formulas, item_name, formula)
#     assert is_valid == expected_valid
#     assert path == expected_path
def test_with_missing_formulas():
    """Test behavior when referenced formulas don't exist"""
    formulas = {'a': 'b + c'}  # c doesn't exist
    is_valid, path = check_circular_reference(formulas, 'new_item', 'a')
    assert is_valid == True
    assert path == []

def test_self_reference():
    """Test direct self-reference"""
    formulas = {'a': '100'}
    is_valid, path = check_circular_reference(formulas, 'a', 'a + 100')
    assert is_valid == False
    assert path == ['a']

def test_multiple_circular_paths():
    """Test case where multiple circular paths exist - should return first one found"""
    formulas = {
        'a': 'b + c',
        'b': 'd',
        'c': 'd',
        'd': 'e'
    }
    is_valid, path = check_circular_reference(formulas, 'e', 'a')
    assert is_valid == False
    # The exact path might depend on implementation details (which dependency is checked first)
    # but it should be one of these two valid paths:
    assert path in [
        ['a', 'b', 'd', 'e' ],  # path through b
        ['a', 'c', 'd', 'e']   # path through c
    ]

def test_complex_formula():
    """Test with complex formula containing operators and parentheses"""
    formulas = {
        'a': 'b + c',
        'b': '100',
        'c': '200'
    }
    is_valid, path = check_circular_reference(formulas, 'new_item', '(a + b) * (c - b) / 100')
    assert is_valid == True
    assert path == []

def test_case_sensitivity():
    """Test that the function is case sensitive"""
    formulas = {
        'Revenue': 'Costs',
        'Costs': '100'
    }
    is_valid, path = check_circular_reference(formulas, 'Profit', 'revenue + costs')
    assert is_valid == True  # Should be true because 'revenue' and 'costs' don't match 'Revenue' and 'Costs'
    assert path == []

def test_empty_formulas():
    """Test with empty formulas dict"""
    is_valid, path = check_circular_reference({}, 'new_item', 'a + b')
    assert is_valid == True
    assert path == []

def test_none_values():
    """Test handling of None values"""
    with pytest.raises((AttributeError, TypeError)):
        check_circular_reference(None, 'item', 'formula')
    
    with pytest.raises((AttributeError, TypeError)):
        check_circular_reference({}, None, 'formula')
    
    with pytest.raises((AttributeError, TypeError)):
        check_circular_reference({}, 'item', None)