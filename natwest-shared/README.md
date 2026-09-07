# natwest-shared

Shared domain and infrastructure library for the NatWest Case Investigation Agent. It defines the database schema, auth contracts, RBAC rules, service logic, and migration/seed entry points used by the backend and MCP server.

## Structure

```
src/natwest_shared/
├── config.py                                              # Shared configuration for database, auth and service runtime settings
│
├── auth/                                                  # Authentication and authorisation
│   ├── keycloak.py                                        # JWT validation against Keycloak and token payload parsing
│   └── rbac.py                                            # NatWest role definitions, permission checks and closure rules
│
├── common/                                                # Shared types, enums and exceptions
│   ├── enums.py                                           # AppRole, case status, customer tier and next-action enums
│   └── exceptions.py                                      # Domain exceptions for auth and permission failures
│
├── db/                                                    # Database model and persistence layer
│   ├── base.py                                            # SQLAlchemy declarative base
│   ├── session.py                                         # Engine and session factory for Postgres access
│   ├── models/                                            # Domain models for users, customers and investigations
│   │   ├── user.py                                        # AppRole and AppUser model definitions
│   │   └── business.py                                   # Customer, Account, Case, Event, Vulnerability and NextAction models
│   ├── repositories/                                      # Data access objects for reads and writes
│   │   ├── user_repository.py                             # User lookup and Keycloak linkage helpers
│   │   ├── business_read_repository.py                    # Read-only repository methods for customer and case data
│   │   └── business_write_repository.py                   # Update and audit-write repository methods
│   └── migrations/                                        # Seed scripts and database bootstrap helpers
│       ├── seed_users.py                                  # Seeds NatWest roles and staff users for local development
│       └── seed_business_data.py                          # Seeds customer, case, account and investigation data
│
├── services/                                              # Business logic layer
│   ├── auth_context_service.py                            # Builds AuthContext from verified JWTs and local user records
│   └── business_service.py                                # Permission-aware service façade for case and customer operations
│
├── schema/                                                # Pydantic schemas for API contracts
│   ├── auth_schema.py                                     # JWT and auth-context schemas
│   ├── business_schema.py                                 # Read models for customer, account, case and action data
│   └── chat_schema.py                                     # Chat request and response payloads
│
├── utils/                                                # Utility helpers
│   └── logger.py                                          # Shared structured logging configuration
│
├── __init__.py                                            # Package marker
└── py.typed                                               # Package typing marker

alembic/                                                   # Alembic migration definitions
├── env.py                                                 # Migration environment configuration
├── README                                                 # Notes on the migration workflow
└── versions/                                              # Versioned schema history
    ├── 97b1ddf51c6c_create_app_roles_and_users.py        # Creates app roles and internal users
    └── 35b4fd9dc5f3_create_business_tables.py             # Creates customer, case and investigation tables

scripts/                                                   # Operational scripts
└── db_entrypoint.sh                                       # Runs migrations and seed tasks during container startup
```

## Domain model

The NatWest case model is centred around the customer and the investigation case:

- `Customer` — customer profile, KYC status, tier, and vulnerability summary
- `Account` — account details and balances attached to a customer
- `Case` — the investigation case, status, priority, type and business context
- `CaseEvent` — chronological operational and system-generated events
- `NextAction` — follow-up work item assigned to a case
- `SourceSystemRecord` — raw alert payloads from external monitoring systems
- `VulnerabilityRegister` — vulnerability and resilience signals tracked against a customer

## RBAC rules

The role model is enforced centrally in `natwest_shared.auth.rbac`:

- `customer_support` — read-only access
- `fraud_investigator` — can read and update active case status
- `case_manager` — can read, update status and manage next actions

Terminal case states such as `resolved` and `closed` are restricted to the case manager path.

## Service behaviour

`BusinessService` is the main permission-aware domain entry point. It validates:

- role access for each operation
- valid status and enum transitions
- existence of the target case or customer
- whether a write action is allowed before a case is terminal

This keeps the business rules in one place and ensures the backend and MCP layers share the same policy model.

## Seed data

The seed layer creates the internal NatWest staff roles and a representative set of customer investigation records for local demos and automated validation.

This includes:

- internal user accounts for support, investigation and case management
- realistic customer records and accounts
- case histories across fraud, dispute and complaint types
- vulnerability/event timeline entries
- next actions with open and completed states

## Local database setup

```bash
cd natwest-shared
uv run python -m natwest_shared.db.migrations.seed_users
uv run python -m natwest_shared.db.migrations.seed_business_data
```

The database layer is intended to run through the Docker stack during normal development, but the individual migration and seed scripts can be executed directly when needed.
