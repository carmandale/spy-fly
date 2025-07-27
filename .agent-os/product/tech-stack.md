# Technical Stack

> Last Updated: 2025-07-26
> Version: 1.0.0

## Core Technologies

### Application Framework
- **Backend Framework:** FastAPI 0.100+
- **Frontend Framework:** React 18+
- **Language (Backend):** Python 3.12+
- **Language (Frontend):** TypeScript 5.0+

### Database System
- **Primary Database:** SQLite 3
- **ORM:** SQLAlchemy 2.0+
- **Migration Tool:** Alembic

### JavaScript Ecosystem
- **Build Tool:** Vite 5.0+
- **Package Manager:** npm
- **Import Strategy:** node
- **State Management:** Zustand
- **Data Fetching:** TanStack Query (React Query)

### UI/UX Stack
- **CSS Framework:** Tailwind CSS v4
- **UI Component Library:** shadcn/ui
- **Charts/Visualization:** Recharts
- **Icons:** Lucide React
- **Fonts Provider:** Local (self-hosted)

### Real-Time Features
- **WebSocket Server:** Starlette WebSockets (built into FastAPI)
- **Task Scheduler:** APScheduler 3.10+
- **Background Jobs:** FastAPI BackgroundTasks

### External APIs
- **Market Data:** Polygon.io (Free tier)
- **VIX Data:** FRED API / AlphaVantage
- **News Sentiment:** NewsAPI (optional)
- **Economic Calendar:** Investing.com scraper

### Development Tools
- **Python Package Manager:** uv (modern Rust-based, 8-10x faster than pip)
- **API Documentation:** FastAPI automatic OpenAPI/Swagger
- **Type Validation:** Pydantic 2.0+
- **Testing (Python):** pytest
- **Testing (React):** Vitest + React Testing Library
- **Testing (E2E):** Playwright
- **Code Formatting:** Black (Python), Prettier (JS/TS)

### Infrastructure
- **Application Hosting:** Local Mac (development)
- **Backend Port:** 8001 (unique to avoid conflicts)
- **Frontend Port:** 5174 (unique to avoid conflicts)
- **Database Hosting:** Local SQLite file
- **Asset Hosting:** Vite dev server (local)
- **Production Build:** Static files served by FastAPI

### Deployment & DevOps
- **Containerization:** Docker + Docker Compose
- **Process Manager:** uvicorn (ASGI server)
- **Environment Management:** python-dotenv
- **Secrets Management:** .env files + OS keyring (for API keys)

### Monitoring & Logging
- **Application Logs:** Python logging module with rotating file handler
- **Metrics Endpoint:** Prometheus format at /metrics
- **Error Tracking:** Local logging (Sentry ready for production)

### Code Repository
- **Version Control:** Git
- **Repository URL:** [To be provided]

## Architecture Decisions

### Why FastAPI + React?
- FastAPI provides automatic API documentation, WebSocket support, and excellent performance
- React with TypeScript ensures type-safe frontend development with a rich ecosystem
- Both are modern, well-documented, and have strong community support

### Why SQLite?
- Perfect for single-user application with ~250 trades/year
- Zero configuration and maintenance
- Easy backup and portability
- SQLAlchemy allows seamless migration to PostgreSQL if needed

### Why Tailwind CSS v4 + shadcn/ui?
- Tailwind v4 provides modern utility-first CSS with improved performance
- shadcn/ui offers accessible, customizable components without vendor lock-in
- Combination provides rapid development with professional results

### Why Local Deployment First?
- Eliminates complexity for MVP development
- No recurring hosting costs
- Complete data privacy and control
- Easy transition to VPS deployment when ready