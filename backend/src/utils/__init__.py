"""
Utils package.

Models Structure:
- All models are Pydantic models (https://pydantic-docs.helpmanual.io/).
- All dates are represented as epoch timestamps (milliseconds since 1970-01-01T00:00:00Z).
- All application-specific IDs are UUIDs (Universally Unique Identifiers).
- All models that need to be persisted to DynamoDB MUST implement:
    - `to_flat_map()`: This method should return a dictionary representation of the model
      where all values are of DynamoDB supported types (String, Number, Binary,
      Boolean, Null, List, Map). Nested Pydantic models should also be flattened.
    - `from_flat_map(data: dict)`: This class method should take a dictionary (as retrieved
      from DynamoDB) and return an instance of the model, building nested pydantic objects as needed.
""" 