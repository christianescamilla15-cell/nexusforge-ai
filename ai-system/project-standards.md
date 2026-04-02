# Project Standards

## Code Quality
- Consistent naming (camelCase for JS/Dart, snake_case for Python)
- Small, focused functions (under 30 lines)
- Self-documenting code — comments only for "why", not "what"

## Git Workflow
- Descriptive commit messages (imperative mood)
- Never force push to main
- Feature branches for non-trivial changes
- Review before merge

## Security
- Never commit secrets (.env, API keys, tokens)
- Use environment variables for all configuration
- Validate input at system boundaries
- Keep dependencies updated
