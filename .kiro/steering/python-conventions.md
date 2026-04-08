---
inclusion: fileMatch
fileMatchPattern: "*.py"
---

# Python Conventions

## Style
- Type hints on all public functions
- f-strings over .format() or %
- pathlib over os.path for file operations

## Architecture
- Async/await for I/O-bound operations
- Dependency injection over global state
- Pydantic for data validation

## Testing
- pytest over unittest
- Fixtures for shared setup
- Mock external services, not internal logic
