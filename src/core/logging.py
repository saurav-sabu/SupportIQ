import logging
import logfire
from src.core.config import get_settings

logger = logging.getLogger(__name__)

def configure_logging(app=None, log_level=logging.INFO):
    """
    Configures standard logging and Pydantic Logfire observability.

    Args:
        app: Optional FastAPI application instance for HTTP auto-instrumentation.
        log_level (int): The logging level to be set. Default is logging.INFO.
    """
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    settings = get_settings()

    token = settings.logfire_token.strip() if settings.logfire_token else None
    if token and (token.startswith("your-") or len(token) < 10):
        token = None


    # Configure Logfire with 'if-token-present' fallback so it runs cleanly offline or in cloud
    logfire.configure(
        service_name=settings.app_name,
        environment=settings.app_env,
        token=token,
        send_to_logfire="if-token-present",
        console=logfire.ConsoleOptions(colors="auto")
    )

    # Auto-instrument all Pydantic models (e.g. RouteDecision, EvidenceGrade, ChatRequest, Settings)
    logfire.instrument_pydantic()

    # Auto-instrument FastAPI routes and middleware if app is provided
    if app is not None:
        logfire.instrument_fastapi(app)
        logger.info("Pydantic Logfire: FastAPI & Pydantic auto-instrumentation active.")