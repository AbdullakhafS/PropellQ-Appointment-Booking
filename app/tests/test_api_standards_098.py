"""
API Standards Tests - Validates all Acceptance Criteria (AC-1 through AC-6)

QA-1: Contract Conformance Validation
QA-2: Error Envelope Validation
QA-3: Idempotency Validation
QA-4: Pagination/Sort Validation
QA-5: Middleware Integration Validation
QA-6: Versioning Governance Validation
"""

import pytest
import json
import uuid
from datetime import datetime, timedelta

from src.api_standards import (
    ApiResponse,
    ErrorDetail,
    ErrorCode,
    PaginationParams,
    PaginatedResponse,
    IdempotencyKey,
    ApiVersion,
    ConformanceValidator,
    ApiStandard,
)
from src.middleware_contract import (
    ErrorHandler,
    ValidationMiddleware,
    AuthMiddleware,
    IdempotencyMiddleware,
    InMemoryIdempotencyStore,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    IdempotencyError,
    MiddlewareException,
    MiddlewareCoordinator,
)


# ============================================================================
# QA-1: Contract Conformance Validation (AC-1)
# ============================================================================

class TestContractConformance:
    """QA-1: Validate endpoints conform to contract template (AC-1, STD-1)."""
    
    def test_standard_response_envelope_has_required_fields(self):
        """Response must have success, correlation_id, timestamp, api_version."""
        response = ApiResponse(
            success=True,
            data={"result": "test"}
        )
        
        response_dict = response.to_dict()
        
        assert "success" in response_dict
        assert "correlation_id" in response_dict
        assert "timestamp" in response_dict
        assert "api_version" in response_dict
    
    def test_success_response_contains_data(self):
        """Successful response must contain data field."""
        test_data = {"appointments": [], "count": 0}
        response = ApiResponse(success=True, data=test_data)
        
        response_dict = response.to_dict()
        assert response_dict["success"] is True
        assert response_dict["data"] == test_data
    
    def test_error_response_contains_error_detail(self):
        """Error response must contain error with code and message."""
        error = ErrorDetail(
            code=ErrorCode.NOT_FOUND,
            message="Resource not found"
        )
        response = ApiResponse(success=False, error=error)
        
        response_dict = response.to_dict()
        assert response_dict["success"] is False
        assert response_dict["error"]["code"] == "NOT_FOUND"
        assert response_dict["error"]["message"] == "Resource not found"
    
    def test_correlation_id_uniqueness(self):
        """Each response should have unique correlation ID."""
        response1 = ApiResponse(success=True, data={})
        response2 = ApiResponse(success=True, data={})
        
        assert response1.correlation_id != response2.correlation_id
    
    def test_timestamp_is_valid_iso_format(self):
        """Response timestamp must be valid ISO format."""
        response = ApiResponse(success=True, data={})
        
        # Should not raise
        datetime.fromisoformat(response.timestamp)
    
    def test_conformance_validator_accepts_valid_response(self):
        """Conformance validator should accept valid response."""
        response_dict = {
            "success": True,
            "data": {"test": "data"},
            "correlation_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "api_version": "1.0"
        }
        
        valid, errors = ConformanceValidator.validate_response_format(response_dict)
        assert valid, f"Valid response rejected: {errors}"
    
    def test_conformance_validator_rejects_missing_success(self):
        """Validator should reject response without success field."""
        response_dict = {
            "data": {"test": "data"},
            "correlation_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "api_version": "1.0"
        }
        
        valid, errors = ConformanceValidator.validate_response_format(response_dict)
        assert not valid
        assert any("success" in e for e in errors)


# ============================================================================
# QA-2: Error Envelope Validation (AC-2)
# ============================================================================

class TestErrorEnvelope:
    """QA-2: Validate standardized envelope across validation/auth/system errors (AC-2, MID-1, MID-2)."""
    
    def test_error_detail_contains_code_and_message(self):
        """Error must have code and message (AC-2)."""
        error = ErrorDetail(
            code=ErrorCode.VALIDATION_ERROR,
            message="Invalid input"
        )
        
        error_dict = error.to_dict()
        assert error_dict["code"] == "VALIDATION_ERROR"
        assert error_dict["message"] == "Invalid input"
    
    def test_error_detail_with_field_information(self):
        """Error can include field for validation errors."""
        error = ErrorDetail(
            code=ErrorCode.INVALID_PARAMETER,
            message="Invalid email format",
            field="email"
        )
        
        error_dict = error.to_dict()
        assert error_dict["field"] == "email"
    
    def test_validation_error_includes_code(self):
        """ValidationError should have VALIDATION_ERROR code."""
        error = ValidationError("Email is required", field="email")
        
        assert error.error_code == ErrorCode.VALIDATION_ERROR
        assert error.field == "email"
    
    def test_authentication_error_has_unauthorized_code(self):
        """AuthenticationError should have UNAUTHORIZED code."""
        error = AuthenticationError("Invalid token")
        
        assert error.error_code == ErrorCode.UNAUTHORIZED
        assert error.status_code == 401
    
    def test_authorization_error_has_forbidden_code(self):
        """AuthorizationError should have FORBIDDEN code."""
        error = AuthorizationError("User lacks permission")
        
        assert error.error_code == ErrorCode.FORBIDDEN
        assert error.status_code == 403
    
    def test_error_handler_converts_exception_to_standard_response(self):
        """ErrorHandler should convert exceptions to standard responses."""
        handler = ErrorHandler()
        error = ValidationError("Invalid input", field="name")
        
        status_code, response = handler.handle_error(error)
        
        assert status_code == 400
        assert response["success"] is False
        assert response["error"]["code"] == "VALIDATION_ERROR"
        assert response["error"]["field"] == "name"
    
    def test_correlation_id_preserved_in_error_response(self):
        """Error response should include correlation ID."""
        handler = ErrorHandler()
        error = ValidationError("Invalid input")
        correlation_id = str(uuid.uuid4())
        
        status_code, response = handler.handle_error(error, correlation_id)
        
        assert response["correlation_id"] == correlation_id


# ============================================================================
# QA-3: Idempotency Validation (AC-3)
# ============================================================================

class TestIdempotency:
    """QA-3: Validate idempotency keys prevent duplicate writes (AC-3, MID-3)."""
    
    def test_idempotency_key_created_from_header(self):
        """IdempotencyKey can be created from header value."""
        key_value = str(uuid.uuid4())
        key = IdempotencyKey.from_header(key_value)
        
        assert key.key == key_value
    
    def test_idempotency_middleware_extracts_key_from_header(self):
        """IdempotencyMiddleware should extract key from Idempotency-Key header."""
        middleware = IdempotencyMiddleware()
        
        environ = {
            "HTTP_IDEMPOTENCY_KEY": str(uuid.uuid4())
        }
        
        extracted_key = middleware.extract_idempotency_key(environ)
        assert extracted_key == environ["HTTP_IDEMPOTENCY_KEY"]
    
    def test_request_hash_computed_consistently(self):
        """Same request should produce same hash."""
        middleware = IdempotencyMiddleware()
        
        body = json.dumps({"name": "John"})
        hash1 = middleware.compute_request_hash(body, "POST", "/api/appointments")
        hash2 = middleware.compute_request_hash(body, "POST", "/api/appointments")
        
        assert hash1 == hash2
    
    def test_different_requests_produce_different_hashes(self):
        """Different requests should produce different hashes."""
        middleware = IdempotencyMiddleware()
        
        body1 = json.dumps({"name": "John"})
        body2 = json.dumps({"name": "Jane"})
        
        hash1 = middleware.compute_request_hash(body1, "POST", "/api/appointments")
        hash2 = middleware.compute_request_hash(body2, "POST", "/api/appointments")
        
        assert hash1 != hash2
    
    def test_duplicate_request_detected(self):
        """Middleware should detect duplicate requests."""
        store = InMemoryIdempotencyStore()
        middleware = IdempotencyMiddleware(store)
        
        idempotency_key = str(uuid.uuid4())
        request_hash = middleware.compute_request_hash(
            json.dumps({"name": "John"}),
            "POST",
            "/api/appointments"
        )
        
        # Record initial response
        response = {"success": True, "id": "123"}
        middleware.record_response(idempotency_key, request_hash, response, 200)
        
        # Check duplicate
        is_duplicate, cached = middleware.check_duplicate(idempotency_key, request_hash)
        
        assert is_duplicate is True
        assert cached.response == response
    
    def test_conflicting_request_raises_error(self):
        """Different request with same key should raise error."""
        store = InMemoryIdempotencyStore()
        middleware = IdempotencyMiddleware(store)
        
        idempotency_key = str(uuid.uuid4())
        
        # Record initial request
        request_hash1 = middleware.compute_request_hash(
            json.dumps({"name": "John"}),
            "POST",
            "/api/appointments"
        )
        response = {"success": True, "id": "123"}
        middleware.record_response(idempotency_key, request_hash1, response, 200)
        
        # Different request with same key
        request_hash2 = middleware.compute_request_hash(
            json.dumps({"name": "Jane"}),
            "POST",
            "/api/appointments"
        )
        
        with pytest.raises(IdempotencyError):
            middleware.check_duplicate(idempotency_key, request_hash2)
    
    def test_expired_idempotency_key_not_replayed(self):
        """Expired idempotency records should not be replayed."""
        store = InMemoryIdempotencyStore(ttl_seconds=0)  # Expire immediately
        middleware = IdempotencyMiddleware(store)
        
        idempotency_key = str(uuid.uuid4())
        request_hash = middleware.compute_request_hash(
            json.dumps({"name": "John"}),
            "POST",
            "/api/appointments"
        )
        
        # Record response
        response = {"success": True, "id": "123"}
        middleware.record_response(idempotency_key, request_hash, response, 200)
        
        # Check duplicate (should be expired)
        is_duplicate, cached = middleware.check_duplicate(idempotency_key, request_hash)
        
        assert is_duplicate is False
        assert cached is None


# ============================================================================
# QA-4: Pagination/Sort Validation (AC-4)
# ============================================================================

class TestPaginationSemantics:
    """QA-4: Validate collection endpoint behavior and pagination (AC-4, STD-2)."""
    
    def test_pagination_params_defaults(self):
        """PaginationParams should have sensible defaults."""
        params = PaginationParams()
        
        assert params.page == 1
        assert params.limit == 20
        assert params.sort_order == "asc"
    
    def test_pagination_params_validates_page(self):
        """Page must be >= 1."""
        params = PaginationParams(page=0)
        assert params.page == 1  # Corrected to 1
    
    def test_pagination_params_validates_limit_minimum(self):
        """Limit must be >= 1."""
        params = PaginationParams(limit=0)
        assert params.limit == 1  # Corrected to 1
    
    def test_pagination_params_validates_limit_maximum(self):
        """Limit should not exceed 100."""
        params = PaginationParams(limit=200)
        assert params.limit == 100  # Capped at 100
    
    def test_pagination_params_validates_sort_order(self):
        """Sort order must be asc or desc."""
        params = PaginationParams(sort_order="invalid")
        assert params.sort_order == "asc"  # Defaults to asc
    
    def test_paginated_response_creates_correct_metadata(self):
        """PaginatedResponse should compute correct metadata."""
        items = [{"id": 1}, {"id": 2}]
        response = PaginatedResponse.create(
            items=items,
            total=42,
            page=2,
            limit=20
        )
        
        assert response.total_pages == 3
        assert response.has_more is True
    
    def test_paginated_response_last_page_no_more(self):
        """Last page should have has_more=False."""
        items = [{"id": 1}]
        response = PaginatedResponse.create(
            items=items,
            total=21,
            page=2,
            limit=20
        )
        
        assert response.has_more is False
    
    def test_paginated_response_format_includes_sort_info(self):
        """Paginated response should include sort information."""
        items = [{"id": 1}]
        response = PaginatedResponse.create(
            items=items,
            total=10,
            page=1,
            limit=20,
            sort_by="created_at",
            sort_order="desc"
        )
        
        response_dict = response.to_dict()
        assert response_dict["sort_by"] == "created_at"
        assert response_dict["sort_order"] == "desc"
    
    def test_conformance_validator_accepts_pagination(self):
        """Validator should accept paginated response format."""
        response_dict = {
            "success": True,
            "data": {
                "items": [{"id": 1}],
                "total": 10,
                "page": 1,
                "limit": 20,
                "total_pages": 1,
                "has_more": False
            },
            "correlation_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "api_version": "1.0"
        }
        
        valid, errors = ConformanceValidator.validate_pagination(response_dict)
        assert valid, f"Valid pagination rejected: {errors}"


# ============================================================================
# QA-5: Middleware Integration Validation (AC-5)
# ============================================================================

class TestMiddlewareIntegration:
    """QA-5: Validate shared middleware behavior (AC-5, MID-1, MID-2, MID-3)."""
    
    def test_validation_middleware_checks_required_fields(self):
        """ValidationMiddleware should verify required fields."""
        middleware = ValidationMiddleware()
        
        request_data = {"name": "John", "email": None}
        schema = {"required": ["name", "email"]}
        
        valid, errors = middleware.validate_request(request_data, schema)
        
        assert not valid
        assert any("email" in e for e in errors)
    
    def test_validation_middleware_checks_field_types(self):
        """ValidationMiddleware should verify field types."""
        middleware = ValidationMiddleware()
        
        request_data = {"age": "not_a_number"}
        schema = {"types": {"age": int}}
        
        valid, errors = middleware.validate_request(request_data, schema)
        
        assert not valid
        assert any("age" in e for e in errors)
    
    def test_auth_middleware_registers_and_verifies_tokens(self):
        """AuthMiddleware should manage tokens."""
        middleware = AuthMiddleware()
        token = str(uuid.uuid4())
        
        user_context = {"user_id": "123", "role": "patient"}
        middleware.register_token(token, user_context)
        
        auth_header = f"Bearer {token}"
        authenticated, context = middleware.authenticate(auth_header, {})
        
        assert authenticated is True
        assert context == user_context
    
    def test_auth_middleware_rejects_invalid_token(self):
        """AuthMiddleware should reject invalid tokens."""
        middleware = AuthMiddleware()
        
        auth_header = f"Bearer invalid_token"
        authenticated, context = middleware.authenticate(auth_header, {})
        
        assert authenticated is False
    
    def test_middleware_coordinator_wraps_handler(self):
        """MiddlewareCoordinator should wrap handlers."""
        coordinator = MiddlewareCoordinator()
        
        def test_handler(environ, start_response, correlation_id):
            return []
        
        wrapped = coordinator.create_middleware_stack(test_handler)
        
        assert callable(wrapped)


# ============================================================================
# QA-6: Versioning Governance Validation (AC-6)
# ============================================================================

class TestVersioning:
    """QA-6: Validate versioning and deprecation policy (AC-6, GOV-2)."""
    
    def test_api_version_can_be_marked_deprecated(self):
        """ApiVersion can be marked as deprecated."""
        version = ApiVersion(
            major=1,
            minor=0,
            patch=0,
            deprecated=True,
            deprecation_date="2026-06-01",
            sunset_date="2026-12-01"
        )
        
        assert version.is_deprecated() is True
    
    def test_current_version_detection(self):
        """Can check if version is current."""
        version = ApiVersion(major=1, minor=0, patch=0)
        
        assert version.is_current("1.0.0") is True
        assert version.is_current("1.0.1") is False
    
    def test_api_standard_manages_versions(self):
        """ApiStandard should manage multiple versions."""
        standard = ApiStandard()
        
        assert standard.get_current_version() is not None
        assert standard.get_version("1.0") is not None
    
    def test_api_standard_creates_conformant_responses(self):
        """ApiStandard should create conformant responses."""
        standard = ApiStandard()
        
        response = standard.create_response(
            success=True,
            data={"test": "data"}
        )
        
        assert response.api_version == standard.get_current_version()
        valid, errors = ConformanceValidator.validate_response_format(response.to_dict())
        assert valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
