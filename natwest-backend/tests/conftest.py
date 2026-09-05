"""Shared pytest fixtures for natwest-backend.

Ensures required Settings() env vars have safe local defaults so unit
tests can import agent modules without depending on a fully configured
shell environment (docker-compose sets these for real deployments).
"""

import os

_DEFAULTS = {
    "MCP_HOST": "localhost",
    "MCP_PORT": "9001",
    "API_HOST": "localhost",
    "API_PORT": "8000",
    "LANGSMITH_TRACING": "false",
    "LANGSMITH_API_KEY": "",
    "LANGSMITH_ENDPOINT": "https://api.smith.langchain.com",
    "LANGSMITH_PROJECT": "test",
    "APP_VERSION": "test",
    "REDIS_URL": "redis://localhost:6379/0",
}

for _key, _value in _DEFAULTS.items():
    os.environ.setdefault(_key, _value)
