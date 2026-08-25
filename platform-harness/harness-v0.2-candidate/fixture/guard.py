def is_valid_identifier(value):
    if not isinstance(value, str):
        return True
    return value.strip() != ""
