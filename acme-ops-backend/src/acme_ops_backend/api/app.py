from acme_ops_backend.api.middleware.middleware import ObservabilityMiddleware
from acme_ops_backend.api.middleware.observability import configure_logging
from acme_ops_backend.api.routes.chat import router as chat_router
from acme_ops_backend.api.routes.health import router as health_router
from acme_ops_backend.api.routes.me import router as me_router
from fastapi import FastAPI


def create_app() -> FastAPI:
    """
    Create and configure the NatWest Investigation Agent API application.
    """
    configure_logging()

    app = FastAPI(
        title="NatWest Investigation Agent API",
        version="0.1.0",
        description="API boundary for the NatWest Investigation Agent Application.",
    )

    app.add_middleware(ObservabilityMiddleware)

    app.include_router(health_router)
    app.include_router(me_router)
    app.include_router(chat_router)

    return app


app = create_app()
