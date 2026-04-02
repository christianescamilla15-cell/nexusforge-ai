---
inclusion: fileMatch
fileMatchPattern: "*.{tsx,jsx,ts,js}"
---

# Frontend Standards

## Component Patterns
- Functional components only — no class components
- Custom hooks for shared logic (useAuth, useFetch, etc.)
- Co-locate styles, tests, and types with components

## State Management
- Use context/hooks for local state
- External store (Redux/Zustand/Riverpod) only for global state
- Avoid prop drilling beyond 2 levels

## Performance
- React.memo for expensive renders
- useMemo/useCallback for stable references
- Lazy load routes and heavy components

## Testing
- Unit test hooks and utils
- Integration test critical user flows
- Snapshot tests for UI regression
