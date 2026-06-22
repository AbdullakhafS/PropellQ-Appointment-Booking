# PIPE-1: Centralized Log Shipping Pipeline

**Status:** Published  
**Version:** 1.0  
**Last Updated:** 2026-06-22  
**Audience:** Platform engineers, DevOps, SRE

---

## 1. Overview

This document specifies the centralized log shipping pipeline that collects structured logs from all services and forwards them to a centralized logging backend for aggregation, storage, and analysis.

**Objectives:**
- Ship logs from all services to centralized backend reliably
- Support multiple sink types (Elasticsearch, Datadog, Splunk, etc.)
- Implement retry and circuit-breaker patterns for resilience
- Minimize performance impact on services
- Enable secure log transmission and authentication

---

## 2. Architecture Overview

### 2.1 Log Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ Services (Appointment, Clinical, Auth, Notification, etc.)      │
│  ├─ Application logs (Serilog, Winston, etc.)                  │
│  ├─ Infrastructure logs (container, system)                    │
│  └─ Audit logs (security events)                               │
└────────────────────────┬────────────────────────────────────────┘
                         │ Structured JSON logs
                         │ (via HTTPS/TLS)
                         ↓
        ┌────────────────────────────────┐
        │  Collector/Forwarder            │
        │  ├─ Fluentd / Fluent Bit       │
        │  ├─ Logstash / Beats           │
        │  └─ Custom Shipper             │
        │                                 │
        │  [Retry Logic]                 │
        │  [Circuit Breaker]             │
        │  [Buffering]                   │
        └────────────────────────────────┘
                         │ Batched logs
                         │ (gzip compression)
                         ↓
        ┌────────────────────────────────┐
        │  Centralized Backend            │
        │  ├─ Elasticsearch               │
        │  ├─ Datadog                    │
        │  ├─ Splunk                     │
        │  └─ CloudWatch / Stackdriver   │
        └────────────────────────────────┘
                         │
                         ↓
        ┌────────────────────────────────┐
        │  Query / Search / Analytics     │
        │  ├─ Kibana (ES)                │
        │  ├─ Datadog UI                 │
        │  └─ Splunk UI                  │
        └────────────────────────────────┘
```

### 2.2 Log Shipping Methods

#### Option A: Direct Service-to-Backend (Recommended for Low Volume)

```
Service Logs
    ↓ (HTTP/HTTPS)
Elasticsearch / Datadog / Splunk
```

**Pros:** Simple, low latency, direct control  
**Cons:** Network overhead per service, scaling issues  
**Use case:** <100 req/sec per service

#### Option B: Collector-Based (Recommended for Production)

```
Service Logs
    ↓ (HTTP or UDP to local collector)
Fluentd / Logstash / Fluent Bit (on each host)
    ↓ (Batched, compressed)
Centralized Backend
```

**Pros:** Buffering, compression, retry logic, efficiency  
**Cons:** Additional infrastructure  
**Use case:** >100 req/sec, high availability required

#### Option C: Sidecar Pattern (Kubernetes)

```
Pod: [Service] [Log Shipper Sidecar]
    ↓
Both containers share log volume
    ↓
Sidecar reads and ships logs
    ↓
Centralized Backend
```

**Pros:** Container-native, graceful shutdown, pod-scoped  
**Cons:** Resource overhead per pod  
**Use case:** Kubernetes clusters

---

## 3. Log Shipping Configuration

### 3.1 Elasticsearch via HTTP

**Configuration for Serilog (C#):**

```csharp
// Appsettings.json
{
  "Serilog": {
    "WriteTo": [
      {
        "Name": "Elasticsearch",
        "Args": {
          "nodeUris": "https://elasticsearch-cluster.propellq.local:9200",
          "indexFormat": "logs-{0:yyyy.MM.dd}",
          "autoRegisterTemplate": true,
          "autoRegisterTemplateVersion": "7",
          "schemaProvider": "Serilog.Sinks.Elasticsearch.ExceptionAsObjectExceptionFormatter",
          "batchPostingLimit": 50,
          "period": "00:00:05",
          "connectionTimeout": 5000,
          "emitEventFailure": "WriteToSelfLog|RaiseException",
          "connection": {
            "Options": {
              "ServerCertificateValidationCallback": "ValidateCertificate"
            }
          },
          "username": "${ELASTICSEARCH_USERNAME}",
          "password": "${ELASTICSEARCH_PASSWORD}"
        }
      }
    ]
  }
}
```

**Implementation Example:**

```csharp
var credentials = new BasicAuthenticationCredentials(
    username: Environment.GetEnvironmentVariable("ELASTICSEARCH_USERNAME"),
    password: Environment.GetEnvironmentVariable("ELASTICSEARCH_PASSWORD"));

var sinkOptions = new ElasticsearchSinkOptions(
    new[] { new Uri("https://elasticsearch.propellq.local:9200") })
{
    IndexFormat = "logs-appointment-service-{0:yyyy.MM.dd}",
    AutoRegisterTemplate = true,
    ModifyConnectionSettings = (conn) => conn
        .BasicAuthentication(credentials.Username, credentials.Password)
        .ServerCertificateValidationCallback((_, _, _, _) => true), // Validate in prod
    BatchPostingLimit = 50,
    Period = TimeSpan.FromSeconds(5),
    FailureCallback = (logEvent) => 
    {
        // Fallback logging
        Console.Error.WriteLine($"Failed to log: {logEvent.MessageTemplate}");
    }
};

var logger = new LoggerConfiguration()
    .WriteTo.Elasticsearch(sinkOptions)
    .Enrich.FromLogContext()
    .CreateLogger();
```

### 3.2 Datadog API

**Configuration for Serilog:**

```csharp
// Appsettings.json
{
  "Serilog": {
    "WriteTo": [
      {
        "Name": "DatadogLogs",
        "Args": {
          "apiKey": "${DATADOG_API_KEY}",
          "source": "appointment-service",
          "service": "appointment-service",
          "environment": "production",
          "site": "datadoghq.com",
          "batchPostingLimit": 100,
          "period": "00:00:10"
        }
      }
    ]
  }
}
```

**Implementation Example:**

```csharp
var datadogOptions = new DatadogLogsOptions
{
    ApiKey = Environment.GetEnvironmentVariable("DATADOG_API_KEY"),
    Source = "appointment-service",
    Service = "appointment-service",
    Environment = "production",
    Site = "datadoghq.com",
    BatchPostingLimit = 100,
    Period = TimeSpan.FromSeconds(10)
};

var logger = new LoggerConfiguration()
    .WriteTo.DatadogLogs(datadogOptions)
    .Enrich.WithProperty("hostname", Environment.MachineName)
    .CreateLogger();
```

### 3.3 Fluentd Configuration (Collector-Based)

**fluent.conf:**

```
# Input from local services via HTTP
<source>
  @type http_rpc
  port 24224
  bind 127.0.0.1
</source>

# Input from services via syslog
<source>
  @type udp
  tag syslog
  <parse>
    @type syslog
    message_format rfc3164
  </parse>
  port 5140
  bind 0.0.0.0
</source>

# Filter to add metadata
<filter **>
  @type record_modifier
  <record>
    hostname "#{Socket.gethostname}"
    environment "#{ENV['ENVIRONMENT']}"
    cluster "#{ENV['CLUSTER_NAME']}"
  </record>
</filter>

# Buffer before sending
<match **>
  @type forward
  send_timeout 60s
  recover_wait 10s
  heartbeat_interval 60s
  
  # Send to Elasticsearch
  <server>
    host elasticsearch.propellq.local
    port 9200
  </server>
  
  # Buffering
  <buffer>
    @type file
    path /var/log/fluentd/buffer/elasticsearch
    flush_interval 10s
    chunk_limit_size 8m
    queue_limit_length 256
    flush_thread_count 2
  </buffer>
  
  # Retry logic
  <secondary>
    @type file
    path /var/log/fluentd/failed/elasticsearch
    <buffer>
      path /var/log/fluentd/buffer/elasticsearch-failed
    </buffer>
  </secondary>
</match>
```

### 3.4 Fluent Bit Configuration (Lightweight)

**fluent-bit.conf:**

```ini
[SERVICE]
    Flush         10
    Daemon        Off
    Log_Level     info
    Parsers_File  parsers.conf
    HTTP_Server   On
    HTTP_Listen   0.0.0.0
    HTTP_Port     2020

# Input from JSON log files
[INPUT]
    Name              tail
    Path              /var/log/containers/*.log
    Parser            docker
    Tag               container.*
    Refresh_Interval  5
    Skip_Long_Lines   On

# Input from systemd
[INPUT]
    Name            systemd
    Tag             systemd.*
    Path            /var/log/journal
    Read_From_Tail  On

# Filter to add metadata
[FILTER]
    Name    modify
    Match   *
    Add     hostname ${HOSTNAME}
    Add     environment ${ENVIRONMENT}
    Add     cluster ${CLUSTER_NAME}

# Output to Elasticsearch
[OUTPUT]
    Name            es
    Match           *
    Host            elasticsearch.propellq.local
    Port            9200
    HTTP_User       ${ELASTICSEARCH_USER}
    HTTP_Passwd     ${ELASTICSEARCH_PASSWORD}
    Index           logs-${service}-${hostname}
    Type            _doc
    Retry_Limit     5
    tls             On
    tls.verify      On
```

---

## 4. Retry and Resilience Patterns

### 4.1 Circuit Breaker Pattern

Prevent cascade failures when backend is unavailable:

```csharp
public class ResilientLogSink
{
    private readonly CircuitBreaker _circuitBreaker;
    private readonly ILogSink _innerSink;

    public ResilientLogSink(ILogSink innerSink)
    {
        _innerSink = innerSink;
        _circuitBreaker = new CircuitBreaker(
            failureThreshold: 5,
            timeout: TimeSpan.FromSeconds(30));
    }

    public void Emit(LogEvent logEvent)
    {
        if (_circuitBreaker.IsOpen)
        {
            // Circuit is open - fail fast
            Console.Error.WriteLine("Log shipping circuit breaker is OPEN");
            LogLocally(logEvent);
            return;
        }

        try
        {
            _innerSink.Emit(logEvent);
            _circuitBreaker.RecordSuccess();
        }
        catch (Exception ex)
        {
            _circuitBreaker.RecordFailure();
            LogLocally(logEvent);
            throw;
        }
    }

    private void LogLocally(LogEvent logEvent)
    {
        // Fallback: write to local file when backend unavailable
        File.AppendAllText("/var/log/fallback.log",
            JsonConvert.SerializeObject(logEvent) + Environment.NewLine);
    }
}
```

### 4.2 Exponential Backoff Retry

```csharp
public async Task<bool> SendLogBatchWithRetryAsync(
    List<LogEvent> batch)
{
    var maxRetries = 5;
    var initialDelay = TimeSpan.FromMilliseconds(100);

    for (int attempt = 0; attempt < maxRetries; attempt++)
    {
        try
        {
            await _httpClient.PostAsync(
                "https://elasticsearch.propellq.local/logs/_bulk",
                new StringContent(SerializeBatch(batch)));
            return true;
        }
        catch (HttpRequestException) when (attempt < maxRetries - 1)
        {
            var delay = TimeSpan.FromMilliseconds(
                initialDelay.TotalMilliseconds * Math.Pow(2, attempt));
            
            _logger.LogWarning(
                "Log shipping failed (attempt {Attempt}). Retrying in {Delay}ms",
                attempt + 1, delay.TotalMilliseconds);

            await Task.Delay(delay);
        }
    }

    // All retries exhausted
    _logger.LogError("Failed to ship logs after {MaxRetries} attempts", maxRetries);
    return false;
}
```

### 4.3 Buffering and Batching

```csharp
public class BatchedLogForwarder
{
    private readonly Channel<LogEvent> _channel;
    private readonly int _batchSize = 100;
    private readonly TimeSpan _flushInterval = TimeSpan.FromSeconds(5);

    public BatchedLogForwarder()
    {
        _channel = Channel.CreateUnbounded<LogEvent>();
        _ = ProcessLogsAsync();
    }

    public void Enqueue(LogEvent logEvent)
    {
        _channel.Writer.TryWrite(logEvent);
    }

    private async Task ProcessLogsAsync()
    {
        var batch = new List<LogEvent>();
        var lastFlush = DateTime.UtcNow;

        await foreach (var logEvent in _channel.Reader.ReadAllAsync())
        {
            batch.Add(logEvent);

            var timeSinceLastFlush = DateTime.UtcNow - lastFlush;

            if (batch.Count >= _batchSize || timeSinceLastFlush > _flushInterval)
            {
                await SendBatchAsync(batch);
                batch.Clear();
                lastFlush = DateTime.UtcNow;
            }
        }
    }

    private async Task SendBatchAsync(List<LogEvent> batch)
    {
        try
        {
            await _httpClient.PostAsync(
                "https://elasticsearch.propellq.local/logs/_bulk",
                CreateBulkRequest(batch));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "Failed to send batch of {Count} logs", batch.Count);
            // Persist to local file as fallback
        }
    }
}
```

---

## 5. Network and Security Configuration

### 5.1 TLS/SSL Enforcement

All log shipping MUST use encrypted connections:

```csharp
// Elasticsearch configuration with TLS
var sinkOptions = new ElasticsearchSinkOptions(
    new[] { new Uri("https://elasticsearch.propellq.local:9200") })
{
    ModifyConnectionSettings = (conn) => conn
        // Use TLS v1.2 or higher
        .ServerCertificateValidationCallback((cert, chain, _, errors) =>
        {
            // Validate certificate chain
            if (errors == System.Net.Security.SslPolicyErrors.None)
                return true;

            // Log certificate validation errors
            _logger.LogError("Certificate validation failed: {Errors}", errors);
            return false;
        })
};
```

### 5.2 Authentication Configuration

Support multiple authentication methods:

```csharp
// Basic authentication (HTTP)
var credentials = new NetworkCredential(
    username: Environment.GetEnvironmentVariable("LOG_SINK_USERNAME"),
    password: Environment.GetEnvironmentVariable("LOG_SINK_PASSWORD"));

// API key authentication (Datadog, Splunk)
var apiKey = Environment.GetEnvironmentVariable("DATADOG_API_KEY");
var headers = new HttpRequestMessage();
headers.Headers.Add("DD-API-KEY", apiKey);

// Certificate-based authentication
var clientCert = new X509Certificate2(
    fileName: Environment.GetEnvironmentVariable("CLIENT_CERT_PATH"),
    password: Environment.GetEnvironmentVariable("CLIENT_CERT_PASSWORD"));
```

### 5.3 Network Policies (Kubernetes)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-logs-egress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  # Allow DNS
  - to:
    - namespaceSelector: {}
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
  
  # Allow logs to Elasticsearch
  - to:
    - namespaceSelector: {}
      podSelector:
        matchLabels:
          app: elasticsearch
    ports:
    - protocol: TCP
      port: 9200
  
  # Allow logs to Datadog
  - to:
    - namespaceSelector:
        matchLabels:
          name: external
    ports:
    - protocol: TCP
      port: 443
```

---

## 6. Deployment Configuration

### 6.1 Docker Deployment

**dockerfile-fluent-bit:**

```dockerfile
FROM fluent/fluent-bit:latest

# Copy configuration
COPY fluent-bit.conf /fluent-bit/etc/
COPY parsers.conf /fluent-bit/etc/

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:2020/api/v1/health || exit 1

# Run Fluent Bit
CMD ["/fluent-bit/bin/fluent-bit", "-c", "/fluent-bit/etc/fluent-bit.conf"]
```

### 6.2 Kubernetes DaemonSet (Fluent Bit)

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
  namespace: logging
spec:
  selector:
    matchLabels:
      app: fluent-bit
  template:
    metadata:
      labels:
        app: fluent-bit
    spec:
      # Run on all nodes including control plane
      tolerations:
      - operator: Exists
      
      containers:
      - name: fluent-bit
        image: fluent/fluent-bit:latest
        
        env:
        - name: ELASTICSEARCH_HOST
          valueFrom:
            configMapKeyRef:
              name: logging-config
              key: elasticsearch_host
        - name: ELASTICSEARCH_USER
          valueFrom:
            secretKeyRef:
              name: logging-credentials
              key: elasticsearch_user
        - name: ELASTICSEARCH_PASSWORD
          valueFrom:
            secretKeyRef:
              name: logging-credentials
              key: elasticsearch_password
        - name: ENVIRONMENT
          value: production
        - name: CLUSTER_NAME
          value: us-east-1
        - name: HOSTNAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        
        volumeMounts:
        - name: varlog
          mountPath: /var/log
          readOnly: true
        - name: config
          mountPath: /fluent-bit/etc/
          readOnly: true
        - name: buffer
          mountPath: /var/log/fluent-bit
        
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 512Mi
        
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 2020
          initialDelaySeconds: 10
          periodSeconds: 30
      
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
      - name: config
        configMap:
          name: fluent-bit-config
      - name: buffer
        hostPath:
          path: /var/log/fluent-bit
          type: DirectoryOrCreate
```

### 6.3 Configuration Management

**ConfigMap for Fluent Bit:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: logging
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush        10
        Daemon       Off
        Log_Level    info
        
    [INPUT]
        Name   tail
        Path   /var/log/containers/*.log
        Tag    container.*
        
    [OUTPUT]
        Name   es
        Match  *
        Host   ${ELASTICSEARCH_HOST}
        Port   9200
        HTTP_User     ${ELASTICSEARCH_USER}
        HTTP_Passwd   ${ELASTICSEARCH_PASSWORD}
```

---

## 7. Monitoring and Metrics

### 7.1 Log Shipping Metrics

Track these metrics for pipeline health:

| Metric | Description | Target |
|--------|-------------|--------|
| `logs_shipped_total` | Total logs successfully shipped | Increment per batch |
| `logs_failed_total` | Failed log shipments | Keep < 0.1% |
| `logs_buffered` | Logs waiting in buffer | < 10K |
| `shipping_latency_ms` | Time from generation to backend | < 1000ms |
| `circuit_breaker_open` | Is circuit breaker open? | False |
| `batch_size_avg` | Average logs per batch | ~100 |

### 7.2 Prometheus Metrics Example

```csharp
public class LogShippingMetrics
{
    private readonly Counter _logsShipped;
    private readonly Counter _logsFailed;
    private readonly Gauge _logsBuffered;
    private readonly Histogram _shippingLatency;

    public LogShippingMetrics()
    {
        _logsShipped = Metrics
            .CreateCounter("logs_shipped_total",
                "Total logs successfully shipped");

        _logsFailed = Metrics
            .CreateCounter("logs_failed_total",
                "Total failed log shipments");

        _logsBuffered = Metrics
            .CreateGauge("logs_buffered",
                "Number of logs currently buffered");

        _shippingLatency = Metrics
            .CreateHistogram("logs_shipping_latency_ms",
                "Log shipping latency in milliseconds",
                new HistogramConfiguration
                {
                    Buckets = new[] { 10, 50, 100, 500, 1000, 5000 }
                });
    }

    public void RecordShippedLogs(int count, double latencyMs)
    {
        _logsShipped.Inc(count);
        _shippingLatency.Observe(latencyMs);
    }

    public void RecordFailedLogs(int count)
    {
        _logsFailed.Inc(count);
    }

    public void SetBufferedLogs(int count)
    {
        _logsBuffered.Set(count);
    }
}
```

---

## 8. Deployment Checklist

- [ ] Centralized backend (Elasticsearch/Datadog/Splunk) deployed and healthy
- [ ] Log shipper/collector configured and running
- [ ] TLS/SSL enabled for all connections
- [ ] Authentication credentials configured and secured
- [ ] Retry and buffering logic in place
- [ ] Circuit breaker configured for resilience
- [ ] Monitoring metrics enabled
- [ ] Log volume tracking in place
- [ ] Fallback local logging configured
- [ ] Network policies allow egress to log backend
- [ ] Backup log storage for unreachable periods

---

## 9. References

- Log Schema: [LOG-1](structured-log-schema-standard.md)
- Correlation Propagation: [LOG-2](correlation-propagation-pattern.md)
- Retention Policy: [PIPE-2](log-retention-delivery-reliability.md)

**Next:** [PIPE-2: Log Retention and Delivery Reliability](log-retention-delivery-reliability.md)
