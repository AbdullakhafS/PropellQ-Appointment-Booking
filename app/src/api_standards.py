"""
API Standards Specification and Enforcement

Defines and enforces the PropellQ API contract including:
- Standard request/response envelopes (AC-1)
- Error response format with correlation IDs (AC-2)
- Collection semantics (AC-4)
- Idempotency patterns (AC-3)
- Versioning and deprecation (AC-6)
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ErrorCode(Enum):
    """Standard machine-readable error codes."""
    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    
    # Authentication/Authorization
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_TOKEN = "INVALID_TOKEN"
    
    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    
    # Idempotency
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    DUPLICATE_REQUEST = "DUPLICATE_REQUEST"
    
    # Server errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    
    # Business logic
    UNAVAILABLE_SLOT = "UNAVAILABLE_SLOT"
    APPOINTMENT_CONFLICT = "APPOINTMENT_CONFLICT"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"


@dataclass
class ErrorDetail:
    """AC-2: Standard error detail with correlation ID and code."""
    code: str | ErrorCode
    message: str
    field: str | None = None
    details: Optional[dict[str, Any]] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        error_dict = {
            "code": self.code.value if isinstance(self.code, ErrorCode) else self.code,
            "message": self.message,
        }
        if self.field:
            error_dict["field"] = self.field
        if self.details:
            error_dict["details"] = self.details
        return error_dict


@dataclass
class ApiResponse:
    """AC-1: Standard API response envelope."""
    success: bool
    data: Any = None
    error: ErrorDetail | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    api_version: str = "1.0"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "success": self.success,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "api_version": self.api_version,
        }
        
        if self.data is not None:
            result["data"] = self.data
        
        if self.error is not None:
            if isinstance(self.error, ErrorDetail):
                result["error"] = self.error.to_dict()
            else:
                result["error"] = self.error
        
        if self.meta:
            result["meta"] = self.meta
        
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class PaginationParams:
    """AC-4: Standard pagination parameters."""
    page: int = 1
    limit: int = 20
    sort_by: str | None = None
    sort_order: str = "asc"
    
    def __post_init__(self):
        """Validate pagination parameters."""
        if self.page < 1:
            self.page = 1
        if self.limit < 1:
            self.limit = 1
        if self.limit > 100:
            self.limit = 100
        if self.sort_order not in ("asc", "desc"):
            self.sort_order = "asc"


@dataclass
class PaginatedResponse:
    """AC-4: Standard paginated collection response."""
    items: list[Any]
    total: int
    page: int
    limit: int
    total_pages: int
    has_more: bool
    sort_by: str | None = None
    sort_order: str = "asc"
    
    @staticmethod
    def create(
        items: list[Any],
        total: int,
        page: int,
        limit: int,
        sort_by: str | None = None,
        sort_order: str = "asc"
    ) -> PaginatedResponse:
        """Factory method to create paginated response."""
        total_pages = (total + limit - 1) // limit
        has_more = page < total_pages
        
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
            has_more=has_more,
            sort_by=sort_by,
            sort_order=sort_order
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "limit": self.limit,
            "total_pages": self.total_pages,
            "has_more": self.has_more,
            "sort_by": self.sort_by,
            "sort_order": self.sort_order,
        }


@dataclass
class IdempotencyKey:
    """AC-3: Idempotency key for preventing duplicate writes."""
    key: str
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    @staticmethod
    def from_header(header_value: str) -> IdempotencyKey:
        """Create idempotency key from HTTP header."""
        return IdempotencyKey(key=header_value)


@dataclass
class ApiVersion:
    """AC-6: API version tracking for deprecation policy."""
    major: int
    minor: int
    patch: int
    deprecated: bool = False
    deprecation_date: str | None = None
    sunset_date: str | None = None
    migration_guide_url: str | None = None
    
    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"
    
    def is_current(self, current_version: str) -> bool:
        """Check if this version is current."""
        parts = current_version.split(".")
        current = (int(parts[0]), int(parts[1]), int(parts[2]))
        mine = (self.major, self.minor, self.patch)
        return mine == current
    
    def is_deprecated(self) -> bool:
        """Check if version is deprecated."""
        return self.deprecated


class ConformanceValidator:
    """Validates API endpoints conform to standards (AC-1, GOV-1)."""
    
    @staticmethod
    def validate_request_envelope(request_data: dict[str, Any], required_fields: list[str] | None = None) -> tuple[bool, list[str]]:
        """
        Validate request conforms to expected structure.
        
        Returns:
            Tuple of (valid, errors)
        """
        errors = []
        
        if not isinstance(request_data, dict):
            errors.append("Request must be a JSON object")
        
        if required_fields:
            for field in required_fields:
                if field not in request_data:
                    errors.append(f"Missing required field: {field}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_response_format(response_data: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate response conforms to standard envelope (AC-1).
        
        Must contain:
        - success (bool)
        - correlation_id (str)
        - timestamp (str)
        - api_version (str)
        - data or error (one required)
        """
        errors = []
        required_fields = ["success", "correlation_id", "timestamp", "api_version"]
        
        for field in required_fields:
            if field not in response_data:
                errors.append(f"Missing required response field: {field}")
        
        if "data" not in response_data and "error" not in response_data:
            errors.append("Response must contain either 'data' or 'error'")
        
        if response_data.get("error") is not None:
            error_obj = response_data["error"]
            if not isinstance(error_obj, dict):
                errors.append("Error must be an object")
            elif "code" not in error_obj or "message" not in error_obj:
                errors.append("Error must contain 'code' and 'message'")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_pagination(response_data: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate paginated response format (AC-4)."""
        errors = []
        
        if "data" in response_data:
            data = response_data["data"]
            required_fields = ["items", "total", "page", "limit", "total_pages", "has_more"]
            
            for field in required_fields:
                if field not in data:
                    errors.append(f"Missing pagination field: {field}")
        
        return len(errors) == 0, errors


class ApiStandard:
    """Singleton managing API standards and contracts."""
    
    _instance: Optional[ApiStandard] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.api_versions = {
            "1.0": ApiVersion(major=1, minor=0, patch=0, deprecated=False),
            "1.1": ApiVersion(major=1, minor=1, patch=0, deprecated=False),
        }
        self.current_version = "1.0"
        self.conformance_enabled = True
    
    def get_current_version(self) -> str:
        """Get current API version."""
        return self.current_version
    
    def set_current_version(self, version: str) -> None:
        """Set current API version."""
        if version in self.api_versions:
            self.current_version = version
    
    def register_version(self, version: ApiVersion) -> None:
        """Register a new API version."""
        self.api_versions[str(version)] = version
    
    def get_version(self, version_str: str) -> ApiVersion | None:
        """Get version information."""
        return self.api_versions.get(version_str)
    
    def create_response(
        self,
        success: bool,
        data: Any = None,
        error: ErrorDetail | None = None,
        meta: dict[str, Any] | None = None,
        correlation_id: str | None = None
    ) -> ApiResponse:
        """Factory method to create standardized response."""
        response = ApiResponse(
            success=success,
            data=data,
            error=error,
            meta=meta or {},
            correlation_id=correlation_id or str(uuid.uuid4()),
            api_version=self.current_version
        )
        
        if self.conformance_enabled:
            valid, errors = ConformanceValidator.validate_response_format(response.to_dict())
            if not valid:
                raise ValueError(f"Response not conformant to standard: {errors}")
        
        return response
