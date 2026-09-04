# natwest-shared

Shared library used by both the backend and MCP server. Contains database models, repositories, services, authentication, RBAC, schemas, and migrations.

## Structure

```
src/natwest_shared/
├── config.py                          # Shared settings (database URL, Keycloak config)
│
├── auth/                              # Authentication and authorisation
│   ├── keycloak.py                    # JWT verification via JWKS, token payload validation
│   └── rbac.py                        # Role definitions (READ, WRITE, ADMIN) and checks
│
├── common/                            # Shared types and exceptions
│   ├── enums.py                       # AppRole, CustomerTier, IssueStatus, IssuePriority, etc.
│   └── exceptions.py                  # AuthError, PermissionDenied, AppUserNotFoundError
│
├── db/                                # Database layer
│   ├── base.py                        # SQLAlchemy declarative base
│   ├── session.py                     # Engine and session factory
│   ├── models/
│   │   ├── user.py                    # AppRole, AppUser models
│   │   └── business.py               # Customer, Issue, IssueUpdate, NextAction models
│   ├── repositories/
│   │   ├── user_repository.py         # User lookup, Keycloak ID linking
│   │   ├── business_read_repository.py  # Read-only queries (customers, issues, updates, actions)
│   │   └── business_write_repository.py # Write operations (status updates, issue updates, actions)
│   └── migrations/
│       ├── seed_users.py              # Seeds 3 roles + 3 users (sales, support, admin)
│       └── seed_business_data.py      # Seeds 3 customers, 4 issues, updates, actions
│
├── services/                          # Business logic
│   ├── auth_context_service.py        # JWT → AuthContext pipeline (verify, resolve, match role)
│   └── business_service.py            # Permission-aware facade over read/write repositories
│
├── schema/                            # Pydantic models
│   ├── auth_schema.py                 # KeycloakTokenPayload, AuthenticatedUser, AuthContext
│   ├── business_schema.py             # CustomerRead, IssueRead, IssueUpdateRead, NextActionRead
│   └── chat_schema.py                 # ChatRequest, ChatResponse
│
└── utils/
    └── logger.py                      # Structured logging configuration

alembic/                               # Database migrations
├── env.py                             # Alembic environment config
└── versions/
    ├── 97b1ddf51c6c_create_app_roles_and_users.py
    └── 35b4fd9dc5f3_create_business_tables.py

scripts/
└── db_entrypoint.sh                   # Migration runner + seed executor for Docker
```

## Database schema

### Users and roles

- **app_roles** — three roles: `sales_user`, `support_user`, `admin`
- **app_users** — linked to Keycloak via `keycloak_user_id`, assigned one role

### Business data

- **customers** — name, industry, tier (smb/mid_market/enterprise), health status, contract value
- **issues** — linked to a customer, external reference (ISSUE-101), status, priority, assignee, due date
- **issue_updates** — timeline entries per issue, with author and customer visibility flag
- **next_actions** — follow-up tasks per issue, typed (customer_update, technical_investigation, etc.), with owner and status

## RBAC model

| Role | Read | Write (issues) | Admin (actions) |
|------|------|----------------|-----------------|
| sales_user | ✅ | ❌ | ❌ |
| support_user | ✅ | ✅ | ❌ |
| admin | ✅ | ✅ | ✅ |

Enforced by `rbac.py` → `require_role()` called in `BusinessService` before every operation.

## Auth flow

1. `KeycloakTokenVerifier` validates JWT signature, expiry, issuer, and client binding
2. `AuthContextService` resolves the app user by username, matches token roles to app role
3. First login links the Keycloak user ID to the app user record
4. Returns `AuthContext(app_user_id, username, role)` used by all downstream services

## Seed data

Example: Three customers pre-loaded for demonstration:

| Customer | Industry | Tier | Health | Issues |
|----------|----------|------|--------|--------|
| Globex Corporation | Financial Services | Enterprise | At risk | ISSUE-101, ISSUE-102 |
| Initech | Technology | Mid-market | Healthy | ISSUE-201 |
| Umbrella Retail | Retail | Enterprise | Watch | ISSUE-301 |
