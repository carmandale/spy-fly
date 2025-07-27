# Technical Specification

This is the technical specification for the spec detailed in @.agent-os/specs/2025-07-26-project-scaffold-#1/spec.md

> Created: 2025-07-26
> Version: 1.0.0

## Technical Requirements

- FastAPI backend with Python 3.12+ support
- React 18+ with TypeScript 5.0+ and Vite 5.0+
- Tailwind CSS v4 with PostCSS configuration
- Docker and docker-compose for containerization
- SQLite database with SQLAlchemy ORM
- Environment variable management with python-dotenv
- CORS configuration for local development
- API versioning structure (v1)
- Modular code organization for scalability

## Approach Options

**Option A:** Monorepo with shared Docker network
- Pros: Single repository, easier dependency management, shared types possible
- Cons: More complex build process, larger repo size

**Option B:** Separate repos linked via docker-compose (Selected)
- Pros: Clean separation of concerns, independent deployment, smaller focused repos
- Cons: Need to manage CORS, no shared types without additional tooling

**Rationale:** Since we're in a single repo but with clear backend/frontend separation, we get the benefits of monorepo management while maintaining architectural boundaries. Docker-compose provides the networking.

## External Dependencies

### Backend Dependencies
- **fastapi[all]** - Web framework with automatic OpenAPI docs
- **sqlalchemy** - ORM for database management
- **python-dotenv** - Environment variable management
- **uvicorn** - ASGI server for FastAPI
- **pydantic** - Data validation and settings management
- **pydantic-settings** - Settings management with environment variables

### Frontend Dependencies
- **react** - UI framework
- **react-dom** - React DOM bindings
- **typescript** - Type safety
- **vite** - Build tool and dev server
- **tailwindcss** - Utility-first CSS framework
- **@vitejs/plugin-react** - React support for Vite
- **autoprefixer** - PostCSS plugin for vendor prefixes
- **postcss** - CSS processing

### Development Dependencies
- **prettier** - Code formatting
- **eslint** - JavaScript/TypeScript linting
- **black** - Python code formatting
- **ruff** - Fast Python linter
- **pytest** - Python testing framework

## Project Structure

```
spy-fly/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI application entry
│   │   ├── config.py         # Settings and configuration
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py       # Dependencies for endpoints
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── api.py    # API router aggregation
│   │   │       └── endpoints/
│   │   │           ├── __init__.py
│   │   │           └── health.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── database.py   # Database configuration
│   │   └── models/
│   │       └── __init__.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── index.css
│   │   ├── api/
│   │   │   └── client.ts     # API client configuration
│   │   ├── components/
│   │   │   └── StatusIndicator.tsx
│   │   └── vite-env.d.ts
│   ├── public/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── Dockerfile
├── docker-compose.yml
├── .gitignore
└── README.md
```

## API Design

### Health Check Endpoint

```
GET /api/v1/health

Response:
{
  "status": "healthy",
  "timestamp": "2025-07-26T12:00:00Z",
  "version": "0.1.0",
  "environment": "development"
}
```

## Docker Configuration

### Backend Dockerfile (Multi-stage)
- Build stage: Install dependencies
- Runtime stage: Copy only necessary files, run with non-root user

### Frontend Dockerfile (Multi-stage)
- Build stage: Install deps and build production bundle
- Runtime stage: Nginx serving static files (production)
- Development: Use Vite dev server

### Docker Compose Services
- **backend**: FastAPI with hot reload, exposed on port 8000
- **frontend**: React dev server with hot reload, exposed on port 3000
- **db**: SQLite volume mount (no separate service needed)

## Environment Variables

### Backend (.env)
```
DATABASE_URL=sqlite:///./spy_fly.db
ENVIRONMENT=development
DEBUG=true
CORS_ORIGINS=["http://localhost:3000"]
```

### Frontend (.env)
```
VITE_API_BASE_URL=http://localhost:8000
```