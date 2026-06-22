"""
Shared Middleware Contracts

Defines the middleware interface contract for:
- Error/Exception handling (MID-1, AC-2, AC-5)
- Validation and Auth (MID-2, AC-5)
- Idempotency (MID-3, AC-3)

All middleware standardizes error responses and correlation ID propagation.
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional
from urllib.parse import parse_qs

from src.api_standards import (
    ApiResponse,
    ErrorDetail,
    ErrorCode,
    IdempotencyKey,
)


# ============================================================================
# MID-1: Error/Exception Middleware Contract
# ============================================================================

class MiddlewareException(Exception):
    """Base exception for middleware operations."""
    
    def __init__(
        self,
        error_code: ErrorCode | str,
        message: str,
        status_code: int = 500,
        field: str | None = None,
        details: dict[str, Any] | None = None
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.field = field
        self.details = details
        super().__init__(message)


class ValidationError(MiddlewareException):
    """Validation middleware error (AC-5)."""
    
    def __init__(
        self,
        message: str,
        field: str | None = None,
        details: dict[str, Any] | None = None
    ):
        super().__init__(
            ErrorCode.VALIDATION_ERROR,
            message,
            status_code=400,
            field=field,
            details=details
        )


class AuthenticationError(MiddlewareException):
    """Authentication middleware error (AC-5)."""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            ErrorCode.UNAUTHORIZED,
            message,
            status_code=401
        )


class AuthorizationError(MiddlewareException):
    """Authorization middleware error (AC-5)."""
    
    def __init__(self, message: str = "Access forbidden"):
        super().__init__(
            ErrorCode.FORBIDDEN,
            message,
            status_code=403
        )


class IdempotencyError(MiddlewareException):
    """Idempotency middleware error (AC-3)."""
    
    def __init__(self, message: str = "Duplicate request detected"):
        super().__init__(
            ErrorCode.DUPLICATE_REQUEST,
            message,
            status_code=409
        )


class ErrorHandler:
    """MID-1: Error handler middleware for standardized error responses (AC-2, AC-5)."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    def handle_error(
        self,
        error: Exception,
        correlation_id: str | None = None
    ) -> tuple[int, dict[str, Any]]:
        """
        Convert exception to standardized error response.
        
        Returns:
            Tuple of (status_code, response_dict)
        """
        if isinstance(error, MiddlewareException):
            status_code = error.status_code
            error_detail = ErrorDetail(
                code=error.error_code,
                message=error.message,
                field=error.field,
                details=error.details
            )
        else:
            status_code = 500
            error_detail = ErrorDetail(
                code=ErrorCode.INTERNAL_ERROR,
                message=str(error) if self.debug else "Internal server error",
                details={"debug": str(error)} if self.debug else None
            )
        
        response = ApiResponse(
            success=False,
            error=error_detail,
            correlation_id=correlation_id
        )
        
        return status_code, response.to_dict()


# ============================================================================
# MID-2: Validation and Auth Middleware Contract
# ============================================================================

class ValidationMiddleware:
    """MID-2: Validation middleware for request validation (AC-5)."""
    
    def __init__(self):
        self.validators: dict[str, Callable] = {}
    
    def register_validator(self, name: str, validator: Callable) -> None:
        """Register a custom validator."""
        self.validators[name] = validator
    
    def validate_required_fields(
        self,
        data: dict[str, Any],
        required_fields: list[str]
    ) -> tuple[bool, list[str]]:
        """
        Validate that required fields are present.
        
        Returns:
            Tuple of (valid, error_messages)
        """
        errors = []
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Missing required field: {field}")
        return len(errors) == 0, errors
    
    def validate_field_types(
        self,
        data: dict[str, Any],
        field_types: dict[str, type]
    ) -> tuple[bool, list[str]]:
        """
        Validate that fields have correct types.
        
        Returns:
            Tuple of (valid, error_messages)
        """
        errors = []
        for field, expected_type in field_types.items():
            if field in data:
                value = data[field]
                if value is not None and not isinstance(value, expected_type):
                    errors.append(f"Field '{field}' must be of type {expected_type.__name__}, got {type(value).__name__}")
        return len(errors) == 0, errors
    
    def validate_request(
        self,
        request_data: dict[str, Any],
        schema: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """
        Validate request against schema.
        
        Schema format:
        {
            "required": ["field1", "field2"],
            "types": {"field1": str, "field2": int},
            "custom": {"field": validator_func}
        }
        """
        errors = []
        
        # Check required fields
        if "required" in schema:
            valid, req_errors = self.validate_required_fields(
                request_data,
                schema["required"]
            )
            errors.extend(req_errors)
        
        # Check field types
        if "types" in schema:
            valid, type_errors = self.validate_field_types(
                request_data,
                schema["types"]
            )
            errors.extend(type_errors)
        
        # Check custom validators
        if "custom" in schema:
            for field, validator in schema["custom"].items():
                if field in request_data:
                    try:
                        if not validator(request_data[field]):
                            errors.append(f"Validation failed for field: {field}")
                    except Exception as e:
                        errors.append(f"Validation error for field '{field}': {str(e)}")
        
        return len(errors) == 0, errors


class AuthMiddleware:
    """MID-2: Authentication middleware contract."""
    
    def __init__(self):
        self.token_store: dict[str, dict[str, Any]] = {}
    
    def authenticate(
        self,
        auth_header: str | None,
        environ: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        """
        Authenticate request from Authorization header.
        
        Returns:
            Tuple of (authenticated, user_context)
        """
        if not auth_header:
            return False, {}
        
        if not auth_header.startswith("Bearer "):
            return False, {}
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        # Verify token exists in store
        if token not in self.token_store:
            return False, {}
        
        return True, self.token_store[token]
    
    def register_token(self, token: str, user_context: dict[str, Any]) -> None:
        """Register an authentication token."""
        self.token_store[token] = user_context
    
    def revoke_token(self, token: str) -> None:
        """Revoke an authentication token."""
        self.token_store.pop(token, None)


# ============================================================================
# MID-3: Idempotency Middleware Contract
# ============================================================================

@dataclass
class IdempotencyRecord:
    """Record of a past idempotent request."""
    key: str
    request_hash: str
    response: dict[str, Any]
    status_code: int
    created_at: str
    expires_at: str


class IdempotencyStore(ABC):
    """Abstract base for idempotency storage."""
    
    @abstractmethod
    def get(self, key: str) -> IdempotencyRecord | None:
        """Retrieve idempotency record by key."""
        pass
    
    @abstractmethod
    def store(self, record: IdempotencyRecord) -> None:
        """Store idempotency record."""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass


class InMemoryIdempotencyStore(IdempotencyStore):
    """In-memory implementation of idempotency store (for testing)."""
    
    def __init__(self, ttl_seconds: int = 86400):
        self.records: dict[str, IdempotencyRecord] = {}
        self.ttl_seconds = ttl_seconds
    
    def get(self, key: str) -> IdempotencyRecord | None:
        """Retrieve record, removing if expired."""
        record = self.records.get(key)
        if record is None:
            return None
        
        # Check expiration
        expiry = datetime.fromisoformat(record.expires_at)
        if datetime.utcnow() > expiry:
            del self.records[key]
            return None
        
        return record
    
    def store(self, record: IdempotencyRecord) -> None:
        """Store record with TTL."""
        self.records[record.key] = record
    
    def exists(self, key: str) -> bool:
        """Check if key exists and not expired."""
        return self.get(key) is not None


class IdempotencyMiddleware:
    """MID-3: Idempotency middleware for safe retries (AC-3)."""
    
    HEADER_KEY = "Idempotency-Key"
    REPLAY_WINDOW_SECONDS = 86400  # 24 hours
    
    def __init__(self, store: IdempotencyStore | None = None):
        self.store = store or InMemoryIdempotencyStore(self.REPLAY_WINDOW_SECONDS)
    
    def extract_idempotency_key(self, environ: dict[str, Any]) -> str | None:
        """Extract idempotency key from request headers."""
        headers = self._parse_headers(environ)
        return headers.get(self.HEADER_KEY.lower())
    
    def compute_request_hash(self, body: str, method: str, path: str) -> str:
        """Compute hash of request for deduplication."""
        hasher = hashlib.sha256()
        hasher.update(f"{method}:{path}:{body}".encode())
        return hasher.hexdigest()
    
    def check_duplicate(
        self,
        idempotency_key: str,
        request_hash: str
    ) -> tuple[bool, IdempotencyRecord | None]:
        """
        Check if this is a duplicate request.
        
        Returns:
            Tuple of (is_duplicate, cached_response)
        """
        record = self.store.get(idempotency_key)
        if record is None:
            return False, None
        
        # If request hash matches, it's a replay
        if record.request_hash == request_hash:
            return True, record
        
        # If hashes differ, it's a conflict (different request with same key)
        raise IdempotencyError(
            f"Conflicting request with Idempotency-Key: {idempotency_key}"
        )
    
    def record_response(
        self,
        idempotency_key: str,
        request_hash: str,
        response: dict[str, Any],
        status_code: int
    ) -> None:
        """Record successful response for future replay."""
        expires_at = (
            datetime.utcnow() + timedelta(seconds=self.REPLAY_WINDOW_SECONDS)
        ).isoformat()
        
        record = IdempotencyRecord(
            key=idempotency_key,
            request_hash=request_hash,
            response=response,
            status_code=status_code,
            created_at=datetime.utcnow().isoformat(),
            expires_at=expires_at
        )
        
        self.store.store(record)
    
    @staticmethod
    def _parse_headers(environ: dict[str, Any]) -> dict[str, str]:
        """Parse HTTP headers from WSGI environ."""
        headers = {}
        for key, value in environ.items():
            if key.startswith("HTTP_"):
                # Remove HTTP_ prefix and convert to lowercase
                header_name = key[5:].replace("_", "-").lower()
                headers[header_name] = value
        return headers


# ============================================================================
# Middleware Coordinator
# ============================================================================

class MiddlewareCoordinator:
    """Coordinates middleware components for request processing."""
    
    def __init__(
        self,
        error_handler: ErrorHandler | None = None,
        validation_middleware: ValidationMiddleware | None = None,
        auth_middleware: AuthMiddleware | None = None,
        idempotency_middleware: IdempotencyMiddleware | None = None
    ):
        self.error_handler = error_handler or ErrorHandler()
        self.validation_middleware = validation_middleware or ValidationMiddleware()
        self.auth_middleware = auth_middleware or AuthMiddleware()
        self.idempotency_middleware = idempotency_middleware or IdempotencyMiddleware()
    
    def create_middleware_stack(
        self,
        handler: Callable
    ) -> Callable:
        """Create a middleware stack around a handler."""
        def middleware_wrapper(environ: dict[str, Any], start_response: Callable) -> Any:
            try:
                # Extract correlation ID from header or generate
                headers = self._parse_headers(environ)
                correlation_id = headers.get("x-correlation-id")
                
                # Call handler
                return handler(environ, start_response, correlation_id)
            except MiddlewareException as e:
                status_code, response = self.error_handler.handle_error(
                    e,
                    correlation_id
                )
                return self._send_error_response(start_response, status_code, response)
            except Exception as e:
                status_code, response = self.error_handler.handle_error(
                    e,
                    correlation_id
                )
                return self._send_error_response(start_response, status_code, response)
        
        return middleware_wrapper
    
    @staticmethod
    def _parse_headers(environ: dict[str, Any]) -> dict[str, str]:
        """Parse HTTP headers from WSGI environ."""
        headers = {}
        for key, value in environ.items():
            if key.startswith("HTTP_"):
                header_name = key[5:].replace("_", "-").lower()
                headers[header_name] = value
        return headers
    
    @staticmethod
    def _send_error_response(
        start_response: Callable,
        status_code: int,
        response: dict[str, Any]
    ) -> list[bytes]:
        """Send standardized error response."""
        body = json.dumps(response).encode("utf-8")
        status_text = {
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            409: "Conflict",
            500: "Internal Server Error"
        }.get(status_code, "Error")
        
        start_response(f"{status_code} {status_text}", [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body)))
        ])
        
        return [body]
