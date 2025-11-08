def add_numbers(a: int, b: int):
    if not isinstance(a, int) or not isinstance(b, int):
        raise TypeError('Both inputs should be integers')
    return a + b


# --- IGNORE ---