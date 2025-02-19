def validate_fields(required_fields, request) -> list:
    """
    Validates that all required fields are present in the request JSON data.

    Args:
        required_fields (list of str): A list of field names that are required to be present in the request JSON data.
        request (Request): The request object containing JSON data to be validated.

    Returns:
        list: A list of field names that are missing from the request JSON data. If all required fields are present,
              an empty list is returned.

    Example:
        required_fields = ['first_name', 'last_name', 'email_address']
        request_json = {'first_name': 'John', 'email_address': 'john@example.com'}
        missing_fields = validate_fields(required_fields, request)
        # missing_fields would be ['last_name']
    """
    return [field for field in required_fields if field not in request.form]