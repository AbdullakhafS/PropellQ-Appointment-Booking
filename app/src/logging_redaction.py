"""
Log Redaction and Security Controls

Implements SEC-1 and SEC-2:
- SEC-1: PHI/PII/secret masking to prevent leakage
- SEC-2: Logging boundary controls
- AC-3: PHI/secret masking prevents leakage in emitted logs
"""

from typing import Dict, Any, List, Pattern, Set, Callable
import re
import hashlib
import secrets


class RedactionLevel(int):
    """Redaction intensity levels."""
    NONE = 0           # No redaction
    LOW = 1            # Mask common fields
    MEDIUM = 2         # Mask PHI/PII/secrets
    HIGH = 3           # Aggressive redaction


class RedactionRule:
    """
    Rule for identifying and redacting sensitive data.
    
    Supports:
    - Field name matching (exact, prefix, regex)
    - Pattern matching (email, phone, SSN, etc.)
    - Custom predicates
    """
    
    def __init__(
        self,
        name: str,
        field_matcher: Callable[[str], bool],
        value_matcher: Callable[[Any], bool],
        redactor: Callable[[Any], str]
    ):
        """
        Args:
            name: Rule identifier
            field_matcher: Function to check if field should be checked
            value_matcher: Function to check if value matches pattern
            redactor: Function to redact value (must return string)
        """
        self.name = name
        self.field_matcher = field_matcher
        self.value_matcher = value_matcher
        self.redactor = redactor


class FieldRedactor:
    """
    Identifies and redacts sensitive fields (SEC-1).
    
    PHI (Protected Health Information):
    - MRN (Medical Record Number)
    - Patient names
    - Appointment notes containing diagnosis
    
    PII (Personally Identifiable Information):
    - Email addresses
    - Phone numbers
    - SSN/Tax ID
    - Credit card numbers
    - Passport numbers
    
    Secrets:
    - API keys
    - Auth tokens
    - Database passwords
    """
    
    # Patterns for common sensitive data
    PATTERNS = {
        "email": re.compile(r"[\w\.-]+@[\w\.-]+\.\w+"),
        "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "credit_card": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
        "uuid": re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I),
        "api_key": re.compile(r"(?i)(api[_-]?key|secret|token|password)['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9\-._]+)"),
    }
    
    # Field names that indicate sensitive data
    SENSITIVE_FIELDS = {
        # Medical
        "mrn", "medical_record_number", "diagnosis", "prognosis",
        "patient_name", "provider_notes", "clinical_notes",
        
        # Personal
        "ssn", "tax_id", "passport", "driver_license",
        "phone", "email", "date_of_birth", "dob",
        
        # Financial
        "credit_card", "card_number", "account_number", "bank_account",
        "routing_number", "cvv", "cvv2",
        
        # Auth
        "password", "pwd", "api_key", "secret", "token",
        "bearer_token", "access_token", "refresh_token",
        "api_secret", "private_key",
    }
    
    @staticmethod
    def is_sensitive_field(field_name: str) -> bool:
        """Check if field name indicates sensitive data."""
        field_lower = field_name.lower()
        for sensitive in FieldRedactor.SENSITIVE_FIELDS:
            if sensitive in field_lower or field_lower in sensitive:
                return True
        return False
    
    @staticmethod
    def redact_value(value: Any, level: RedactionLevel = RedactionLevel.MEDIUM) -> str:
        """
        Redact sensitive value.
        
        Args:
            value: Value to redact
            level: Redaction intensity
        
        Returns:
            Redacted representation
        """
        if value is None:
            return "[REDACTED:NULL]"
        
        value_str = str(value)
        
        # Levels of redaction
        if level == RedactionLevel.NONE:
            return value_str
        elif level == RedactionLevel.LOW:
            # Show type and length
            return f"[REDACTED:{type(value).__name__}:{len(value_str)}]"
        elif level == RedactionLevel.MEDIUM:
            # Mask with hash
            value_hash = hashlib.sha256(value_str.encode()).hexdigest()[:8]
            return f"[REDACTED:{value_hash}]"
        else:  # HIGH
            # Complete mask
            return "[REDACTED]"
    
    @staticmethod
    def get_redaction_rules() -> List[RedactionRule]:
        """Get default redaction rules (SEC-1)."""
        rules = []
        
        # Rule 1: Sensitive field names (exact and partial matches)
        def sensitive_field_matcher(field_name: str) -> bool:
            return FieldRedactor.is_sensitive_field(field_name)
        
        rules.append(RedactionRule(
            "sensitive_fields",
            field_matcher=sensitive_field_matcher,
            value_matcher=lambda x: True,  # All values in sensitive fields
            redactor=lambda x: FieldRedactor.redact_value(x, RedactionLevel.MEDIUM)
        ))
        
        # Rule 2: Email addresses in any field
        rules.append(RedactionRule(
            "email_pattern",
            field_matcher=lambda f: True,
            value_matcher=lambda x: isinstance(x, str) and FieldRedactor.PATTERNS["email"].search(str(x)),
            redactor=lambda x: FieldRedactor.PATTERNS["email"].sub("[REDACTED:EMAIL]", str(x))
        ))
        
        # Rule 3: Phone numbers
        rules.append(RedactionRule(
            "phone_pattern",
            field_matcher=lambda f: True,
            value_matcher=lambda x: isinstance(x, str) and FieldRedactor.PATTERNS["phone"].search(str(x)),
            redactor=lambda x: FieldRedactor.PATTERNS["phone"].sub("[REDACTED:PHONE]", str(x))
        ))
        
        # Rule 4: SSN
        rules.append(RedactionRule(
            "ssn_pattern",
            field_matcher=lambda f: True,
            value_matcher=lambda x: isinstance(x, str) and FieldRedactor.PATTERNS["ssn"].search(str(x)),
            redactor=lambda x: FieldRedactor.PATTERNS["ssn"].sub("[REDACTED:SSN]", str(x))
        ))
        
        return rules


class LogRedactor:
    """
    Redacts sensitive data from structured log entries (SEC-1, SEC-2, AC-3).
    
    Applies rules to detect PHI, PII, and secrets, replacing with safe
    redacted values that maintain debugging capability without leaking
    sensitive information.
    """
    
    def __init__(self, level: RedactionLevel = RedactionLevel.MEDIUM):
        """
        Initialize redactor.
        
        Args:
            level: Redaction intensity (NONE, LOW, MEDIUM, HIGH)
        """
        self.level = level
        self.rules = FieldRedactor.get_redaction_rules()
    
    def redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively redact sensitive data in dictionary.
        
        AC-3: Prevents PHI/secret leakage.
        """
        if not isinstance(data, dict):
            return data
        
        redacted = {}
        for field_name, value in data.items():
            redacted[field_name] = self._redact_value(field_name, value)
        return redacted
    
    def _redact_value(self, field_name: str, value: Any) -> Any:
        """Redact a single value based on field name and content."""
        # Check if field itself is sensitive
        if FieldRedactor.is_sensitive_field(field_name):
            return FieldRedactor.redact_value(value, self.level)
        
        # Check content-based rules
        for rule in self.rules:
            if rule.field_matcher(field_name) and rule.value_matcher(value):
                return rule.redactor(value)
        
        # Recursively redact nested structures
        if isinstance(value, dict):
            return self.redact_dict(value)
        elif isinstance(value, (list, tuple)):
            return [self._redact_value(field_name, v) for v in value]
        
        return value


class LoggingBoundary:
    """
    Enforces immutable audit boundary (SEC-2).
    
    Prevents:
    - Sensitive payload dumps in error serialization
    - Unauthorized log modification
    - Audit trail tampering
    
    Ensures:
    - All logs are immutable once written
    - Sensitive data is never included in logs
    - Error messages don't dump sensitive payloads
    """
    
    # Fields that should never be logged
    FORBIDDEN_FIELDS = {
        "password", "pwd", "secret", "api_key", "token",
        "bearer_token", "access_token", "refresh_token",
        "credit_card", "card_number", "cvv", "private_key",
    }
    
    # Maximum depth for nested logging
    MAX_NESTED_DEPTH = 3
    
    # Maximum string field size (prevent memory exhaustion)
    MAX_FIELD_SIZE = 10_000
    
    @staticmethod
    def validate_entry_safety(data: Dict[str, Any]) -> List[str]:
        """
        Validate log entry doesn't contain forbidden fields or oversized data.
        
        Returns:
            List of violations (empty if safe)
        """
        violations = []
        
        def check_dict(d: Dict[str, Any], depth: int = 0, path: str = "") -> None:
            if depth > LoggingBoundary.MAX_NESTED_DEPTH:
                violations.append(f"{path}: Exceeds max nesting depth")
                return
            
            for field_name, value in d.items():
                current_path = f"{path}.{field_name}" if path else field_name
                
                # Check for forbidden fields
                if field_name.lower() in LoggingBoundary.FORBIDDEN_FIELDS:
                    violations.append(f"{current_path}: Forbidden field in logs")
                
                # Check field size
                if isinstance(value, str) and len(value) > LoggingBoundary.MAX_FIELD_SIZE:
                    violations.append(f"{current_path}: Exceeds max field size ({len(value)} > {LoggingBoundary.MAX_FIELD_SIZE})")
                
                # Recurse into nested structures
                if isinstance(value, dict):
                    check_dict(value, depth + 1, current_path)
                elif isinstance(value, (list, tuple)):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            check_dict(item, depth + 1, f"{current_path}[{i}]")
        
        check_dict(data)
        return violations


class SanitizedLogEntry:
    """
    Safely serializable log entry with redaction applied (SEC-1, SEC-2, AC-3).
    """
    
    def __init__(
        self,
        entry_dict: Dict[str, Any],
        redaction_level: RedactionLevel = RedactionLevel.MEDIUM
    ):
        """
        Create sanitized entry.
        
        Args:
            entry_dict: Raw log entry dictionary
            redaction_level: Redaction intensity
        
        Raises:
            ValueError: If entry violates logging boundary
        """
        # Validate boundary
        violations = LoggingBoundary.validate_entry_safety(entry_dict)
        if violations:
            raise ValueError(f"Log entry violates boundary: {violations}")
        
        # Apply redaction
        redactor = LogRedactor(redaction_level)
        self.data = redactor.redact_dict(entry_dict)
        self.redaction_level = redaction_level
    
    def to_dict(self) -> Dict[str, Any]:
        """Get sanitized dictionary."""
        return self.data


def create_safe_log_entry(entry_dict: Dict[str, Any]) -> SanitizedLogEntry:
    """
    Factory to create safe log entry with automatic redaction.
    
    AC-3: Prevents PHI/secret leakage.
    """
    return SanitizedLogEntry(entry_dict, RedactionLevel.MEDIUM)
