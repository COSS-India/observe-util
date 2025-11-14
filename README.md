# observe-util

> **Enterprise-grade monitoring and metrics collection for Dhruva Platform deployments**

---

## 🎯 Overview

The `observe-util` package provides comprehensive observability, monitoring, and metrics tracking for FastAPI applications. It enables **multi-tenant metrics collection** with organization-level isolation, automatic service detection, and real-time analytics through Prometheus and Grafana.

This package is designed for the **Dhruva Platform** and provides plug-and-play monitoring capabilities.

---

## ✨ Key Features

- **Multi-tenant metrics collection** with organization-level isolation
- **Automatic service detection** (Translation-NMT, Text to Speech-TTS, Speech to Text-ASR, Image to Text-OCR, Named Entity Recognition-NER, Transliteration, Text Language detection )
- **Real-time monitoring** via Prometheus and Grafana
- **Business metrics** - Characters, Tokens, Audio Length, Image size processed
- **Easy integration** - Few lines of code to get started
- **Plug-and-play** - Works with any FastAPI application
- **Pre-built Grafana dashboards** for instant visualization

---

## 📦 What's Included

- **Metrics Configuration**: Three built-in metrics for Latency, Error rate, Payload Size and the ability to configure customised metrics
- **FastAPI Middleware**: Automatic request tracking and organization identification
- **Prometheus Integration**: Native Prometheus metrics endpoint
- **Grafana Dashboards**: Pre-configured dashboard templates
- **Multi-organization Support**: Tenant isolation for SaaS deployments
- **JWT-based Organization Extraction**: Automatic tenant identification from tokens

---

## 🚀 Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Integration with Dhruva

#### Step 1: Place the Package

Copy the `observe/` folder into your Dhruva project's `server/` directory:

```bash
dhruva/
├── server/
│   ├── observe/           # Place the observe folder here
│   │   ├── __init__.py
│   │   ├── plugin.py
│   │   ├── middleware.py
│   │   ├── metrics.py
│   │   ├── config.py
│   │   └── dashboard-templates/
│   └── main.py           # Your Dhruva FastAPI app
```

#### Step 2: Import and Register in `server/main.py`

Add these lines to your Dhruva FastAPI application:

```python
from fastapi import FastAPI
from observe import ObservabilityPlugin

app = FastAPI()

# Initialize and register observability
enterprise = ObservabilityPlugin()
enterprise.register_plugin(app)

# Your existing routes work unchanged
@app.get("/")
def read_root():
    return {"message": "Hello World"}

# All requests are now automatically tracked!
```

**This creates these endpoints automatically:**
- `/enterprise/metrics` - Prometheus metrics endpoint
- `/enterprise/health` - Health check
- `/enterprise/config` - Configuration details

#### Step 3: Configure Environment Variables

Set these environment variables before starting Dhruva:

```bash
# Required
export OBSERVE_UTIL_ENABLED=true

# Optional
export OBSERVE_UTIL_DEBUG=true
export OBSERVE_UTIL_METRICS_PATH=/enterprise/metrics
export OBSERVE_UTIL_HEALTH_PATH=/enterprise/health
export OBSERVE_UTIL_COLLECT_SYSTEM_METRICS=true
export OBSERVE_UTIL_COLLECT_GPU_METRICS=true
export OBSERVE_UTIL_COLLECT_DB_METRICS=true
```

---

## 📊 Monitoring Stack Setup

### 1. Prometheus Configuration

Add this to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: "dhruva-observability"
    scrape_interval: 5s
    static_configs:
      - targets: ["your-dhruva-host:8000"]
    metrics_path: "/enterprise/metrics"
```

### 2. Grafana Dashboard

- Import pre-built dashboard templates from `observe/dashboard-templates/`
- Create custom dashboards using PromQL queries on metrics defined in `observe/metrics.py`
- Filter metrics by organization for multi-tenant isolation

---

## 📖 Documentation

For detailed documentation, configuration options, and advanced usage, see the **[wiki](./wiki)** file.

The wiki includes:
- Detailed installation and setup instructions
- Organization identification and JWT token configuration
- Complete environment variable reference
- Prometheus and Grafana integration guide
- Custom dashboard creation with PromQL examples
- Troubleshooting and debugging tips
- Security best practices

---

## 🔗 Related Projects

### Observe Portal (UI for Team & Dashboard Management)

For a complete observability platform with UI for team management, dashboard display, and role-based access control, check out the **Observe Portal**:

**[https://github.com/COSS-India/observe](https://github.com/COSS-India/observe/tree/main)**

The Observe Portal provides:
- Web-based UI for managing Grafana dashboards
- Team and user management interface
- Role-based access control to dashboards
- Organization management
- Dashboard folder organization

This `observe-util` package complements the Observe Portal by providing the backend metrics collection and instrumentation for FastAPI applications.

---

## 🛠️ What Gets Tracked

Once integrated, the middleware automatically tracks:

### Request Metrics
- Total requests by organization/app/endpoint
- Request duration (histograms)
- Error counts and rates
- Status code distribution

### Service Metrics
- Service-specific requests (Translation, TTS, ASR, etc.)
- Component latency tracking
- Service availability

### Business Metrics
- **TTS**: Characters synthesized
- **Translation**: Characters translated
- **ASR**: Audio seconds processed
- **NER**: Tokens processed
- **Transliteration**: Characters processed
- **Text Language Detection**: Characters processed
- **OCR**: Size of Image processed


### System Metrics
- CPU usage
- Memory usage
- Peak throughput
- Active connections

---

## ⚠️ Prerequisites

### Organization Identification Required

Before using this package, you **MUST** implement organization extraction. The system needs to identify which organization/tenant each request belongs to.

**Recommended**: Use JWT tokens with organization claims:

```python
payload = {
    "sub": "user@example.com",
    "organization": "your-organization-name",  # Required!
    "name": "Organization Display Name",
    "exp": 1234567890
}
```

The middleware checks for these fields in order: `organization`, `org`, `name`, `company`

---

## 🎯 Use Cases

- **Multi-tenant SaaS Monitoring**: Track metrics per organization with complete isolation
- **Service Performance Tracking**: Monitor Translation, TTS, ASR service latencies
- **Business Analytics**: Track characters processed, audio seconds, tokens
- **SLA Monitoring**: Real-time alerts and dashboards for SLA compliance
- **Resource Utilization**: CPU, memory, GPU metrics per tenant

---
