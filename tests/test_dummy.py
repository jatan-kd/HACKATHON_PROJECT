import pytest

from src.dummy import add_numbers


# Test cases for add_numbers function
def test_add_numbers_positive_numbers():
    assert add_numbers(3, 5) == 8


def test_add_numbers_negative_numbers():
    assert add_numbers(-3, -5) == -8


def test_add_numbers_mixed_sign_numbers():
    assert add_numbers(-3, 5) == 2


def test_add_numbers_zero():
    assert add_numbers(0, 0) == 0


# Testing for exceptions
def test_add_numbers_string_input():
    with pytest.raises(TypeError):
        add_numbers('a', 5)     