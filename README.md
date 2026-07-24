# sport-rent-backend

Backend application for a sports equipment rental platform.  
The service exposes a REST API for the frontend application and stores data in a PostgreSQL database using SQLAlchemy.

Built with:
- FastAPI
- PostgreSQL
- SQLAlchemy
- uv package manager

## Features
### Authentication
- User registration
- User login
- Native FastAPI authentication mechanisms
- Protected endpoints for authenticated users

### Product Catalog
- Paginated product list with filtering
- Product details endpoint
- Product availability calendar

### Orders
- Creating rental orders
- Validating product availability for selected rental dates
- Order-related business logic

### Loyalty Program
- Tracking loyalty point history
- Recording earned points
- Recording spent points
- Redeeming loyalty points for orders

### Billing Addresses
- Saving and managing billing address data
- Associating billing information with user accounts and orders

### Favourite Products
- Adding products to a favourites list
- Removing products from favourites
- Retrieving a user’s favourite products

## Requirements
Before running the project, make sure you have installed:
- Python 3.11+ (or the version specified in pyproject.toml)
- uv
- PostgreSQL

## Running the Application
Start the development server with:
```bash
uv run --env-file .env uvicorn app.main:app --reload
```
The API will be available at:
```bash
http://127.0.0.1:8000
```

Interactive API documentation:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Running the Tests

Start PostgreSQL and run the integration tests:

```bash
docker compose up -d db
uv run --env-file .env pytest
```

The tests use `TEST_DATABASE_URL` when it is set, otherwise they fall back to
`DATABASE_URL`. They create a unique PostgreSQL schema for the test run and
remove it afterwards, so application data in the public schema is not modified.

## Suggested project structure

```
.
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── auth.py
│   │   │   ├── products.py
│   │   │   ├── orders.py
│   │   │   ├── loyalty.py
│   │   │   ├── billing_addresses.py
│   │   │   └── favourites.py
│   │   ├── auth_helpers.py
│   │   └── dependencies.py
│   ├── core/
│   │   ├── config.py
│   │   ├── passwords.py
│   │   └── tokens.py
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── main.py
├── migrations/
├── tests/
├── .env.example
├── pyproject.toml
├── uv.lock
└── README.md
```
