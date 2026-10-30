"""Standard error format (SAD section 4.4). Owner: Member 3 (Ronit).

Every error response has the same JSON shape: {code, message, timestamp, traceId}.
Raise `AppError(status_code, "SOME_CODE", "Readable message")` from services and routers.
Normal `HTTPException`s and request-validation errors are converted to the same shape.
"""
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _body(code: str, message: str) -> dict:
    return {
        "code": code,
        "message": message,
        "detail": message,  # same text, so clients and tests that expect FastAPI's usual `detail` keep working
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "traceId": uuid.uuid4().hex,
    }


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content=_body(exc.code, exc.message))

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=_body(f"HTTP_{exc.status_code}", str(exc.detail)),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        problems = "; ".join(
            f"{'.'.join(str(part) for part in err['loc'][1:])}: {err['msg']}" for err in exc.errors()
        )
        return JSONResponse(status_code=400, content=_body("VALIDATION_ERROR", problems))
