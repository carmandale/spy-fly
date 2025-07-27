# SPY-FLY Trading Automation

An automated trading system for SPY 0-DTE bull-call-spread strategies, focusing on educational and simulation purposes.

## Features

- Automated morning sentiment analysis
- Smart spread selection algorithm
- Real-time P/L monitoring
- Risk management with position sizing
- Performance tracking and reporting

## Tech Stack

- **Backend**: FastAPI (Python 3.12+)
- **Frontend**: React 18 with TypeScript and Vite
- **Database**: SQLite with SQLAlchemy
- **Styling**: Tailwind CSS v4
- **Containerization**: Docker & Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Git
- API keys for market data providers (see `.env.example`)

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd spy-fly
   ```

2. Copy environment files:
   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```

3. Add your API keys to `backend/.env`

4. Start the application:
   ```bash
   docker-compose up
   ```

5. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Development

### Backend Development

The backend uses FastAPI with hot reloading enabled. Any changes to Python files will automatically restart the server.

```bash
# Run tests
docker-compose exec backend pytest

# Format code
docker-compose exec backend black app/

# Lint code
docker-compose exec backend ruff app/
```

### Frontend Development

The frontend uses Vite for fast development with hot module replacement.

```bash
# Run tests
docker-compose exec frontend npm test

# Build for production
docker-compose exec frontend npm run build
```

### Project Structure

```
spy-fly/
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── core/         # Core functionality
│   │   ├── models/       # Database models
│   │   └── main.py       # FastAPI application
│   ├── tests/            # Test suite
│   └── requirements.txt  # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── api/          # API client
│   │   ├── components/   # React components
│   │   └── App.tsx       # Main application
│   └── package.json      # Node dependencies
└── docker-compose.yml    # Container orchestration
```

## Testing

Both backend and frontend have comprehensive test suites:

```bash
# Run all tests
docker-compose exec backend pytest
docker-compose exec frontend npm test

# Run with coverage
docker-compose exec backend pytest --cov=app
docker-compose exec frontend npm test -- --coverage
```

## Contributing

1. Create a GitHub issue for your feature/fix
2. Create a feature branch from `main`
3. Make your changes with tests
4. Submit a pull request linking to the issue

## License

[License details to be added]

## Disclaimer

This software is for educational and simulation purposes only. It does not provide financial advice or execute real trades. Always consult with a qualified financial advisor before making investment decisions.