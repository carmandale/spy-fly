# Tests Specification

This is the tests coverage details for the spec detailed in @.agent-os/specs/2025-07-26-project-scaffold-#1/spec.md

> Created: 2025-07-26
> Version: 1.0.0

## Test Coverage

### Unit Tests

**Backend Configuration (test_config.py)**
- Settings load from environment variables
- Default values are applied when env vars missing
- CORS origins are parsed correctly from env

**Health Endpoint (test_health.py)**
- Returns 200 status code
- Response contains all required fields
- Timestamp is valid ISO format
- Version matches configured version

### Integration Tests

**API Client Integration**
- Frontend successfully connects to backend health endpoint
- CORS headers are properly set for local development
- API base URL is correctly configured from environment

**Docker Environment**
- Both services start without errors
- Services can communicate over Docker network
- Hot reload works for both frontend and backend changes
- Environment variables are properly passed to containers

### Feature Tests

**Developer Workflow**
- Clone repo → copy .env.example → docker-compose up completes successfully
- Making changes to backend code triggers automatic reload
- Making changes to frontend code triggers automatic reload
- API documentation is accessible at /docs

### Mocking Requirements

- **Environment Variables:** Mock different configurations to test settings loading
- **Time:** Mock datetime for consistent timestamp testing in health endpoint
- **HTTP Requests:** Mock fetch API in frontend tests to avoid real network calls

## Test Commands

### Backend Tests
```bash
docker-compose exec backend pytest
```

### Frontend Tests
```bash
docker-compose exec frontend npm test
```

### Full Test Suite
```bash
docker-compose run --rm backend pytest
docker-compose run --rm frontend npm test
```

## Test Structure

### Backend Test Organization
```
backend/
└── tests/
    ├── __init__.py
    ├── conftest.py          # Shared fixtures
    ├── unit/
    │   ├── __init__.py
    │   ├── test_config.py
    │   └── test_health.py
    └── integration/
        ├── __init__.py
        └── test_api.py
```

### Frontend Test Organization
```
frontend/
└── src/
    └── __tests__/
        ├── App.test.tsx
        ├── api/
        │   └── client.test.ts
        └── components/
            └── StatusIndicator.test.tsx
```

## Coverage Requirements

- Minimum 80% code coverage for unit tests
- All API endpoints must have integration tests
- All React components must have at least snapshot tests
- Critical business logic requires 100% coverage