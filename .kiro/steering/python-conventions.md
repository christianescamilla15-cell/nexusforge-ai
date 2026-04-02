---
inclusion: fileMatch
fileMatchPattern: "*.py"
---

# Python Conventions

## Style
- Type hints on all public functions
- Docstrings on modules, classes, and public methods
- f-strings over .format() or %
- pathlib over os.path

## Architecture
- Async/await for I/O-bound operations
- Dependency injection over global state
- Pydantic for data validation

## Testing
- pytest over unittest
- Fixtures for shared setup
- Parametrize for multiple inputs
- Mock external services, not internal logic
