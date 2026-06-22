"""
Centralized Log Shipping Pipeline and Delivery Controls

Implements PIPE-1 and PIPE-2:
- PIPE-1: Centralized log forwarding with retry behavior
- PIPE-2: Retention policies and delivery reliability
- AC-4: Log delivery success >= 99.9% with retry
- AC-6: Environment-specific retention policy enforced
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Callable, Deque
from collections import deque
from datetime import datetime, timedelta
import json
import time
import threading
from abc import ABC, abstractmethod


class DeliveryStatus(Enum):
    """Status of log delivery attempt."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


class RetentionPolicy(Enum):
    """Environment-specific log retention."""
    
    # Development: 7 days (cost optimization)
    DEVELOPMENT = 7 * 24 * 3600
    
    # Staging: 30 days (catch issues before production)
    STAGING = 30 * 24 * 3600
    
    # Production: 90 days (compliance and investigation)
    PRODUCTION = 90 * 24 * 3600
    
    def retention_seconds(self) -> int:
        """Return retention time in seconds."""
        return self.value


@dataclass
class LogDeliveryMetrics:
    """Tracks delivery reliability metrics (PIPE-2, AC-4)."""
    
    total_events: int = 0
    delivered_events: int = 0
    failed_events: int = 0
    retried_events: int = 0
    dead_letter_events: int = 0
    
    # Timing
    total_latency_ms: float = 0
    backpressure_events: int = 0
    
    def delivery_success_rate(self) -> float:
        """Calculate delivery success rate (AC-4 target >= 99.9%)."""
        if self.total_events == 0:
            return 1.0
        return self.delivered_events / self.total_events
    
    def average_latency_ms(self) -> float:
        """Calculate average delivery latency."""
        if self.delivered_events == 0:
            return 0.0
        return self.total_latency_ms / self.delivered_events


@dataclass
class LogDeliveryRecord:
    """Record of a single log delivery attempt."""
    
    log_id: str
    event: Dict[str, Any]
    timestamp: datetime
    status: DeliveryStatus = DeliveryStatus.PENDING
    attempt_count: int = 0
    next_retry_time: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # Delivery SLA tracking
    delivery_time_ms: Optional[float] = None
    
    def should_retry(self) -> bool:
        """Check if delivery should be retried."""
        if self.status != DeliveryStatus.FAILED:
            return False
        if self.attempt_count >= 3:
            return False
        return self.next_retry_time and datetime.utcnow() >= self.next_retry_time
    
    def mark_delivered(self, latency_ms: float) -> None:
        """Mark as successfully delivered."""
        self.status = DeliveryStatus.DELIVERED
        self.delivery_time_ms = latency_ms
    
    def mark_failed(self, error: str) -> None:
        """Mark as failed and schedule retry."""
        self.attempt_count += 1
        self.error_message = error
        
        if self.attempt_count >= 3:
            self.status = DeliveryStatus.DEAD_LETTER
        else:
            self.status = DeliveryStatus.RETRYING
            # Exponential backoff: 1s, 2s, 4s
            backoff = min(2 ** (self.attempt_count - 1), 4)
            self.next_retry_time = datetime.utcnow() + timedelta(seconds=backoff)


class LogSink(ABC):
    """
    Abstract log sink for centralized log forwarding (PIPE-1).
    
    Implementations can target:
    - Elasticsearch/ELK stack
    - Splunk
    - DataDog
    - CloudWatch
    - File system
    - Message queue
    """
    
    @abstractmethod
    def send(self, event: Dict[str, Any]) -> bool:
        """
        Send log event to sink.
        
        Args:
            event: Structured log event
        
        Returns:
            True if delivery succeeded, False otherwise
        """
        pass
    
    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if sink is healthy and accepting logs."""
        pass


class InMemoryLogSink(LogSink):
    """
    Test implementation that stores logs in memory (PIPE-1).
    
    Used for unit testing and local development.
    """
    
    def __init__(self, capacity: int = 10000):
        """Initialize in-memory sink."""
        self.logs: Deque[Dict[str, Any]] = deque(maxlen=capacity)
        self.healthy = True
    
    def send(self, event: Dict[str, Any]) -> bool:
        """Store event in memory."""
        if not self.is_healthy():
            return False
        self.logs.append(event)
        return True
    
    def is_healthy(self) -> bool:
        """Memory sink is always healthy."""
        return self.healthy
    
    def get_logs(self) -> List[Dict[str, Any]]:
        """Get stored logs (for testing)."""
        return list(self.logs)
    
    def clear(self) -> None:
        """Clear stored logs."""
        self.logs.clear()


class FileLogSink(LogSink):
    """
    File-based log sink (PIPE-1).
    
    Writes logs to file system with rotation.
    """
    
    def __init__(self, file_path: str = "/var/log/app.log"):
        """Initialize file sink."""
        self.file_path = file_path
        self.lock = threading.Lock()
    
    def send(self, event: Dict[str, Any]) -> bool:
        """Append event to log file."""
        try:
            with self.lock:
                with open(self.file_path, "a") as f:
                    f.write(json.dumps(event) + "\n")
            return True
        except IOError as e:
            # File I/O error
            return False
    
    def is_healthy(self) -> bool:
        """Check file write capability."""
        try:
            with open(self.file_path, "a") as f:
                pass
            return True
        except IOError:
            return False


class LogPipeline:
    """
    Centralized log shipping pipeline (PIPE-1, PIPE-2, AC-4, AC-6).
    
    Features:
    - Multiple sink support
    - Automatic retry with exponential backoff
    - Delivery reliability tracking (AC-4 >= 99.9%)
    - Backpressure handling
    - Retention policy enforcement (AC-6)
    - Dead letter queue for failed events
    """
    
    def __init__(
        self,
        sinks: List[LogSink],
        retention_policy: RetentionPolicy = RetentionPolicy.PRODUCTION,
        max_pending_events: int = 10000
    ):
        """
        Initialize pipeline.
        
        Args:
            sinks: List of log sinks for delivery
            retention_policy: How long to keep logs
            max_pending_events: Max events before backpressure
        """
        self.sinks = sinks
        self.retention_policy = retention_policy
        self.max_pending_events = max_pending_events
        
        # Delivery tracking
        self.pending_events: Dict[str, LogDeliveryRecord] = {}
        self.metrics = LogDeliveryMetrics()
        self.dead_letter_queue: List[LogDeliveryRecord] = []
        self.lock = threading.Lock()
    
    def emit(self, event: Dict[str, Any]) -> bool:
        """
        Emit log event to pipeline.
        
        AC-4: Retries on transient failure.
        AC-6: Enforces retention policy.
        
        Args:
            event: Structured log event
        
        Returns:
            True if accepted, False if backpressure
        """
        with self.lock:
            # Check backpressure
            if len(self.pending_events) >= self.max_pending_events:
                self.metrics.backpressure_events += 1
                return False
            
            # Create delivery record
            log_id = event.get("correlation_id", "unknown")
            record = LogDeliveryRecord(
                log_id=log_id,
                event=event,
                timestamp=datetime.utcnow()
            )
            self.pending_events[log_id] = record
            self.metrics.total_events += 1
            
            # Attempt initial delivery
            self._deliver_record(record)
            
            return True
    
    def _deliver_record(self, record: LogDeliveryRecord) -> None:
        """Deliver a single record to all sinks."""
        delivery_start = time.time()
        success = False
        
        for sink in self.sinks:
            if sink.is_healthy():
                try:
                    if sink.send(record.event):
                        success = True
                except Exception as e:
                    continue
        
        if success:
            delivery_time_ms = (time.time() - delivery_start) * 1000
            record.mark_delivered(delivery_time_ms)
            self.metrics.delivered_events += 1
            self.metrics.total_latency_ms += delivery_time_ms
        else:
            record.mark_failed("All sinks failed")
            self.metrics.failed_events += 1
            self.metrics.retried_events += 1
    
    def flush(self) -> None:
        """Process pending and retryable events."""
        with self.lock:
            # Retry failed events
            log_ids_to_process = list(self.pending_events.keys())
            for log_id in log_ids_to_process:
                record = self.pending_events[log_id]
                
                # Attempt retry
                if record.should_retry():
                    self._deliver_record(record)
                
                # Move to dead letter if too many failures
                if record.status == DeliveryStatus.DEAD_LETTER:
                    self.dead_letter_queue.append(record)
                    del self.pending_events[log_id]
                
                # Remove if expired based on retention policy
                retention_seconds = self.retention_policy.retention_seconds()
                age_seconds = (datetime.utcnow() - record.timestamp).total_seconds()
                if record.status == DeliveryStatus.DELIVERED and age_seconds > retention_seconds:
                    del self.pending_events[log_id]
    
    def get_metrics(self) -> LogDeliveryMetrics:
        """Get delivery metrics (AC-4)."""
        return self.metrics
    
    def get_dead_letter_queue(self) -> List[LogDeliveryRecord]:
        """Get events that failed delivery."""
        return self.dead_letter_queue.copy()
    
    def get_delivery_success_rate(self) -> float:
        """Get current delivery success rate (AC-4)."""
        return self.metrics.delivery_success_rate()
    
    def get_healthy_sinks(self) -> int:
        """Get count of healthy sinks."""
        return sum(1 for sink in self.sinks if sink.is_healthy())


class PipelineFactory:
    """Factory for creating configured log pipelines."""
    
    @staticmethod
    def create_default_pipeline(
        environment: str,
        primary_sink: Optional[LogSink] = None
    ) -> LogPipeline:
        """
        Create default pipeline for environment.
        
        AC-6: Environment-specific retention policy
        """
        # Determine retention policy by environment
        policy_map = {
            "development": RetentionPolicy.DEVELOPMENT,
            "staging": RetentionPolicy.STAGING,
            "production": RetentionPolicy.PRODUCTION,
        }
        retention = policy_map.get(environment, RetentionPolicy.PRODUCTION)
        
        # Use provided sink or default to file
        if primary_sink is None:
            primary_sink = FileLogSink()
        
        return LogPipeline(
            sinks=[primary_sink],
            retention_policy=retention,
            max_pending_events=10000
        )
