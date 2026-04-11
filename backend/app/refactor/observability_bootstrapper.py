# -*- coding: utf-8 -*-
"""Observability stack bootstrapper (Gap 11 from the vision doc).

Emits a drop-in bundle that establishes a modern observability
stack on a service: SLO definitions, Prometheus scrape + alerting
rules, Grafana dashboards, OpenTelemetry collector config,
instrumentation guides for FastAPI and ASP.NET Core, runbook
templates, and a docker-compose for running the stack locally.

Why this exists
===============

Real modernization programs defer observability until a production
incident proves they need it. By then the team is debugging blind.
This generator gives them a coherent baseline on day one:

- **4 golden signals** (latency, traffic, errors, saturation) wired
  into a Grafana dashboard automatically.
- **Two SLO definitions** (API latency, availability) with error
  budget burn alerts that fire before the SLO is breached, not
  after.
- **OpenTelemetry Collector** config covering traces + metrics +
  logs in one pipeline, so the team can swap backends (Jaeger,
  Tempo, Datadog, Honeycomb) without rewiring instrumentation.
- **Runbook templates** for the two alerts the generator actually
  emits, plus a blank template for new ones. Runbooks are the
  difference between a page and a resolution.
- **Local docker-compose stack** so any engineer can run Prometheus
  + Grafana + OTel Collector on their laptop to test
  instrumentation before pushing.

Generated layout:

    out_dir/
    ├── slo/
    │   ├── api_latency.yaml
    │   ├── api_availability.yaml
    │   └── error_budget.md
    ├── prometheus/
    │   ├── prometheus.yml
    │   └── alerts.yml
    ├── grafana/
    │   ├── dashboards/
    │   │   ├── service_overview.json
    │   │   └── error_budget.json
    │   └── datasources/
    │       └── prometheus.yml
    ├── otel/
    │   ├── collector-config.yaml
    │   ├── instrumentation-python.md
    │   └── instrumentation-dotnet.md
    ├── runbooks/
    │   ├── high_latency.md
    │   ├── error_budget_burn.md
    │   └── template.md
    ├── docker-compose.observability.yml
    └── README.md

Everything is language-agnostic except the two instrumentation
guides. Teams on Java / Go / Rust can add their own guides following
the same pattern.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Result dataclass ───────────────────────────────────────────────────────


@dataclass
class GeneratedObservability:
    out_dir: str
    service_name: str
    files_written: list[str] = field(default_factory=list)
    slos_generated: int = 0
    dashboards_generated: int = 0
    runbooks_generated: int = 0

    def to_dict(self) -> dict:
        return {
            "out_dir": self.out_dir,
            "service_name": self.service_name,
            "files_written": self.files_written,
            "slos_generated": self.slos_generated,
            "dashboards_generated": self.dashboards_generated,
            "runbooks_generated": self.runbooks_generated,
        }


# ── SLO definitions ────────────────────────────────────────────────────────


_SLO_LATENCY_TEMPLATE = """# SLO — API request latency
#
# Objective: 99% of HTTP requests to {service_name} complete in
# under 500 ms over any 30-day window.
#
# Format follows the sloth spec (https://sloth.dev) which the
# generator's docker-compose stack includes as an optional image.
# If you do not use sloth, read this file as documentation — the
# Prometheus alert rules in prometheus/alerts.yml cover the same
# intent directly.

version: "prometheus/v1"
service: "{service_name}"
labels:
  owner: "CHANGEME-team"
  tier: "tier-1"
slos:
  - name: "api-latency-p99"
    objective: 99.0
    description: |
      99% of HTTP requests complete in under 500 ms. Measured
      over the request duration histogram exposed by the service
      at /metrics.
    sli:
      events:
        error_query: |
          sum(rate(http_request_duration_seconds_bucket{{job="{service_name}",le="0.5"}}[{{.window}}])) -
          sum(rate(http_request_duration_seconds_bucket{{job="{service_name}",le="+Inf"}}[{{.window}}]))
        total_query: |
          sum(rate(http_request_duration_seconds_bucket{{job="{service_name}",le="+Inf"}}[{{.window}}]))
    alerting:
      name: "{service_name}HighLatency"
      labels:
        severity: page
      annotations:
        summary: "{service_name} p99 latency exceeds 500ms"
        runbook_url: "runbooks/high_latency.md"
      page_alert:
        labels:
          severity: critical
      ticket_alert:
        labels:
          severity: warning
"""


_SLO_AVAILABILITY_TEMPLATE = """# SLO — API availability
#
# Objective: 99.9% of HTTP requests return a non-5xx status code
# over any 30-day window. This is the classic "three nines"
# availability target and allows roughly 43 minutes of error
# budget per 30-day window.

version: "prometheus/v1"
service: "{service_name}"
labels:
  owner: "CHANGEME-team"
  tier: "tier-1"
slos:
  - name: "api-availability"
    objective: 99.9
    description: |
      99.9% of HTTP requests return a non-5xx response. 5xx
      responses count as errors; 4xx and redirects do not.
    sli:
      events:
        error_query: |
          sum(rate(http_requests_total{{job="{service_name}",status=~"5.."}}[{{.window}}]))
        total_query: |
          sum(rate(http_requests_total{{job="{service_name}"}}[{{.window}}]))
    alerting:
      name: "{service_name}ErrorBudgetBurn"
      labels:
        severity: page
      annotations:
        summary: "{service_name} error budget burning fast"
        runbook_url: "runbooks/error_budget_burn.md"
      page_alert:
        labels:
          severity: critical
      ticket_alert:
        labels:
          severity: warning
"""


_ERROR_BUDGET_DOC = """# Error budget explained

## What is an error budget?

An error budget is the complement of an SLO. If your SLO says
"99.9% of requests succeed", then 0.1% of requests are allowed to
fail without breaching the objective. That 0.1% is the error
budget — a finite resource that the team spends over a rolling
window (typically 30 days).

## Why it matters

Without an error budget, teams either:

1. Over-invest in reliability (every 5xx is treated as a P0),
   which starves feature work, or
2. Under-invest in reliability (5xx responses get batched as
   "we'll look at it later"), which ships degraded experiences.

An error budget turns reliability into a quantifiable budget
that the team spends deliberately. When the budget is healthy,
ship features fast. When the budget is low, slow down and fix
reliability until the budget recovers.

## How much budget you have

For 99.9% availability over 30 days (the generated SLO):

- 30 days = 43,200 minutes
- 0.1% budget = 43.2 minutes of downtime allowed per window
- Equivalently, ~1,440 seconds of errors per month

Burn rate is the speed at which you are consuming the budget.
A burn rate of 1 means you will exactly exhaust the budget over
the 30-day window. A burn rate of 10 means you are burning 10x
faster and will exhaust the budget in 3 days.

## Alert policy

The generated Prometheus alerts use a **multi-window, multi-burn-rate**
pattern (the pattern Google recommends in their SRE workbook):

- **Fast burn alert**: fires when the 1-hour burn rate exceeds 14.4
  AND the 5-minute burn rate exceeds 14.4. This catches incidents
  that would exhaust 2% of the budget in 1 hour.
- **Slow burn alert**: fires when the 6-hour burn rate exceeds 6
  AND the 30-minute burn rate exceeds 6. This catches slower
  regressions that would exhaust 5% of the budget over 6 hours.

Both alerts page on-call. The two windows in each alert act as a
debounce — a brief spike does not page, but a sustained problem does.

## How to use this in a team meeting

- **Weekly**: review the last 7 days' burn rate. If you burned more
  than 14%, you are on track to exhaust the budget before the
  30-day window closes. Slow feature work, focus on reliability.
- **Post-incident**: the budget consumed by the incident is the
  "blast radius" metric for the postmortem. Incidents that consume
  >20% of the monthly budget warrant a P0 followup.
- **Feature freeze trigger**: when the remaining budget drops below
  10% with more than 7 days left in the window, freeze non-essential
  feature deploys until reliability improves.

## How to change the objective

If the 99.9% target is too strict (you are burning budget constantly),
review whether 99.9% is actually what users need. Most tier-2
services can live at 99.5% without users noticing. Relaxing the
objective is a conscious decision — document it in the SLO file's
description and inform stakeholders. Do NOT silently relax it by
tuning alerts.
"""


# ── Prometheus ─────────────────────────────────────────────────────────────


_PROMETHEUS_YML = """# Prometheus scrape configuration

global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    environment: CHANGEME

rule_files:
  - "alerts.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - "alertmanager:9093"

scrape_configs:
  # ── The service being observed ─────────────────────────────────
  - job_name: "{service_name}"
    metrics_path: /metrics
    scrape_interval: 10s
    static_configs:
      - targets:
          - "CHANGEME-host:CHANGEME-port"
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        replacement: "{service_name}"

  # ── OpenTelemetry Collector (forwards metrics) ─────────────────
  - job_name: "otel-collector"
    static_configs:
      - targets:
          - "otel-collector:8889"

  # ── Prometheus self-scrape ─────────────────────────────────────
  - job_name: "prometheus"
    static_configs:
      - targets:
          - "localhost:9090"
"""


_PROMETHEUS_ALERTS = """# Prometheus alerting rules — SLO-aware
#
# Uses the multi-window multi-burn-rate pattern from the Google SRE
# workbook. Each SLO fires two alerts: a fast burn (for acute
# incidents) and a slow burn (for gradual regressions). Both page
# on-call.
#
# Read docs/error_budget.md for the budget math.

groups:
  - name: {service_name}-golden-signals
    rules:
      # ── Latency: p99 > 500ms for 5 minutes ────────────────────
      - alert: {service_name_alert}HighLatencyP99
        expr: |
          histogram_quantile(0.99,
            sum(rate(http_request_duration_seconds_bucket{{job="{service_name}"}}[5m]))
            by (le)
          ) > 0.5
        for: 5m
        labels:
          severity: warning
          service: {service_name}
        annotations:
          summary: "p99 latency for {service_name} is above 500ms"
          description: |
            Current p99: {{{{ $value | humanizeDuration }}}}
            Threshold:    500ms
            SLO:          api-latency-p99 (99%% of requests < 500ms)
          runbook_url: "runbooks/high_latency.md"

      # ── Error rate: > 1% 5xx responses for 5 minutes ─────────
      - alert: {service_name_alert}HighErrorRate
        expr: |
          (
            sum(rate(http_requests_total{{job="{service_name}",status=~"5.."}}[5m]))
            /
            sum(rate(http_requests_total{{job="{service_name}"}}[5m]))
          ) > 0.01
        for: 5m
        labels:
          severity: warning
          service: {service_name}
        annotations:
          summary: "5xx rate for {service_name} above 1%"
          description: |
            Current error rate: {{{{ $value | humanizePercentage }}}}
            Threshold: 1%%
          runbook_url: "runbooks/error_budget_burn.md"

  - name: {service_name}-slo-budget-burn
    rules:
      # ── Fast burn: 2% budget in 1h (multi-window) ─────────────
      - alert: {service_name_alert}ErrorBudgetBurnFast
        expr: |
          (
            (
              sum(rate(http_requests_total{{job="{service_name}",status=~"5.."}}[1h]))
              /
              sum(rate(http_requests_total{{job="{service_name}"}}[1h]))
            ) > (14.4 * 0.001)
          )
          and
          (
            (
              sum(rate(http_requests_total{{job="{service_name}",status=~"5.."}}[5m]))
              /
              sum(rate(http_requests_total{{job="{service_name}"}}[5m]))
            ) > (14.4 * 0.001)
          )
        for: 2m
        labels:
          severity: critical
          service: {service_name}
          burn_rate: fast
        annotations:
          summary: "{service_name} burning error budget 14.4x faster than sustainable"
          description: |
            At this rate the 30-day error budget will be exhausted
            in under 2 days. Page the on-call engineer.
          runbook_url: "runbooks/error_budget_burn.md"

      # ── Slow burn: 5% budget in 6h (multi-window) ─────────────
      - alert: {service_name_alert}ErrorBudgetBurnSlow
        expr: |
          (
            (
              sum(rate(http_requests_total{{job="{service_name}",status=~"5.."}}[6h]))
              /
              sum(rate(http_requests_total{{job="{service_name}"}}[6h]))
            ) > (6 * 0.001)
          )
          and
          (
            (
              sum(rate(http_requests_total{{job="{service_name}",status=~"5.."}}[30m]))
              /
              sum(rate(http_requests_total{{job="{service_name}"}}[30m]))
            ) > (6 * 0.001)
          )
        for: 15m
        labels:
          severity: warning
          service: {service_name}
          burn_rate: slow
        annotations:
          summary: "{service_name} slow error budget burn detected"
          description: |
            Burn rate is 6x sustainable over 6 hours. The 30-day
            budget will last 5 days at this rate.
          runbook_url: "runbooks/error_budget_burn.md"
"""


# ── Grafana dashboards ─────────────────────────────────────────────────────


def _service_overview_dashboard(service_name: str) -> dict:
    """Golden-signals dashboard: latency, traffic, errors, saturation."""
    return {
        "annotations": {"list": []},
        "editable": True,
        "graphTooltip": 1,
        "schemaVersion": 38,
        "tags": ["generated", "golden-signals", service_name],
        "templating": {"list": []},
        "time": {"from": "now-6h", "to": "now"},
        "timepicker": {},
        "timezone": "browser",
        "title": f"{service_name} — service overview",
        "uid": f"{service_name}-overview",
        "version": 1,
        "refresh": "30s",
        "panels": [
            {
                "id": 1,
                "title": "Request rate (req/s)",
                "type": "timeseries",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                "targets": [{
                    "expr": f'sum(rate(http_requests_total{{job="{service_name}"}}[5m]))',
                    "refId": "A",
                    "legendFormat": "total",
                }],
                "fieldConfig": {"defaults": {"unit": "reqps"}, "overrides": []},
            },
            {
                "id": 2,
                "title": "p99 latency (ms)",
                "type": "timeseries",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                "targets": [{
                    "expr": (
                        f'histogram_quantile(0.99, '
                        f'sum(rate(http_request_duration_seconds_bucket'
                        f'{{job="{service_name}"}}[5m])) by (le)) * 1000'
                    ),
                    "refId": "A",
                    "legendFormat": "p99",
                }],
                "fieldConfig": {
                    "defaults": {
                        "unit": "ms",
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {"color": "green", "value": None},
                                {"color": "yellow", "value": 300},
                                {"color": "red", "value": 500},
                            ],
                        },
                    },
                    "overrides": [],
                },
            },
            {
                "id": 3,
                "title": "Error rate (% 5xx)",
                "type": "timeseries",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                "targets": [{
                    "expr": (
                        f'(sum(rate(http_requests_total{{job="{service_name}",status=~"5.."}}[5m])) / '
                        f'sum(rate(http_requests_total{{job="{service_name}"}}[5m]))) * 100'
                    ),
                    "refId": "A",
                    "legendFormat": "5xx %",
                }],
                "fieldConfig": {
                    "defaults": {
                        "unit": "percent",
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {"color": "green", "value": None},
                                {"color": "yellow", "value": 0.5},
                                {"color": "red", "value": 1.0},
                            ],
                        },
                    },
                    "overrides": [],
                },
            },
            {
                "id": 4,
                "title": "Saturation: CPU usage",
                "type": "timeseries",
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                "targets": [{
                    "expr": f'rate(process_cpu_seconds_total{{job="{service_name}"}}[5m])',
                    "refId": "A",
                    "legendFormat": "cpu",
                }],
                "fieldConfig": {"defaults": {"unit": "percentunit"}, "overrides": []},
            },
        ],
    }


def _error_budget_dashboard(service_name: str) -> dict:
    """SLO-focused dashboard: remaining error budget + burn rate."""
    return {
        "annotations": {"list": []},
        "editable": True,
        "schemaVersion": 38,
        "tags": ["generated", "slo", service_name],
        "time": {"from": "now-30d", "to": "now"},
        "timezone": "browser",
        "title": f"{service_name} — error budget",
        "uid": f"{service_name}-error-budget",
        "version": 1,
        "refresh": "1m",
        "panels": [
            {
                "id": 1,
                "title": "Availability SLI (last 30 days)",
                "type": "stat",
                "gridPos": {"h": 6, "w": 8, "x": 0, "y": 0},
                "targets": [{
                    "expr": (
                        f'(1 - (sum(rate(http_requests_total{{job="{service_name}",status=~"5.."}}[30d])) / '
                        f'sum(rate(http_requests_total{{job="{service_name}"}}[30d])))) * 100'
                    ),
                    "refId": "A",
                }],
                "fieldConfig": {
                    "defaults": {
                        "unit": "percent",
                        "min": 99,
                        "max": 100,
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {"color": "red", "value": None},
                                {"color": "yellow", "value": 99.9},
                                {"color": "green", "value": 99.95},
                            ],
                        },
                    },
                    "overrides": [],
                },
            },
            {
                "id": 2,
                "title": "Error budget remaining",
                "type": "gauge",
                "gridPos": {"h": 6, "w": 8, "x": 8, "y": 0},
                "targets": [{
                    "expr": (
                        f'((0.001 - (sum(rate(http_requests_total{{job="{service_name}",status=~"5.."}}[30d])) / '
                        f'sum(rate(http_requests_total{{job="{service_name}"}}[30d])))) / 0.001) * 100'
                    ),
                    "refId": "A",
                }],
                "fieldConfig": {
                    "defaults": {
                        "unit": "percent",
                        "min": 0,
                        "max": 100,
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {"color": "red", "value": None},
                                {"color": "yellow", "value": 25},
                                {"color": "green", "value": 50},
                            ],
                        },
                    },
                    "overrides": [],
                },
            },
            {
                "id": 3,
                "title": "Burn rate (1h vs 6h)",
                "type": "timeseries",
                "gridPos": {"h": 8, "w": 24, "x": 0, "y": 6},
                "targets": [
                    {
                        "expr": (
                            f'sum(rate(http_requests_total{{job="{service_name}",status=~"5.."}}[1h])) / '
                            f'sum(rate(http_requests_total{{job="{service_name}"}}[1h])) / 0.001'
                        ),
                        "refId": "A",
                        "legendFormat": "1h",
                    },
                    {
                        "expr": (
                            f'sum(rate(http_requests_total{{job="{service_name}",status=~"5.."}}[6h])) / '
                            f'sum(rate(http_requests_total{{job="{service_name}"}}[6h])) / 0.001'
                        ),
                        "refId": "B",
                        "legendFormat": "6h",
                    },
                ],
                "fieldConfig": {"defaults": {"unit": "short"}, "overrides": []},
            },
        ],
    }


_GRAFANA_DATASOURCE = """apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
    jsonData:
      timeInterval: "15s"
"""


# ── OpenTelemetry Collector ────────────────────────────────────────────────


_OTEL_COLLECTOR_CONFIG = """# OpenTelemetry Collector configuration
#
# Single pipeline covering traces + metrics + logs. Swap the
# exporters to point at your chosen backends (Jaeger, Tempo,
# Datadog, Honeycomb, etc.) without touching the service
# instrumentation.

receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

  # Scrape the service's own /metrics endpoint so we can forward to
  # Prometheus remote_write if the team later chooses a hosted Prom.
  prometheus:
    config:
      scrape_configs:
        - job_name: "{service_name}"
          scrape_interval: 15s
          static_configs:
            - targets: ["CHANGEME-host:CHANGEME-port"]

processors:
  batch:
    timeout: 5s
    send_batch_size: 1024
  memory_limiter:
    check_interval: 5s
    limit_percentage: 75
    spike_limit_percentage: 15
  resource:
    attributes:
      - key: service.name
        value: "{service_name}"
        action: upsert
      - key: deployment.environment
        value: "CHANGEME"
        action: upsert

exporters:
  # Prometheus exporter — scraped by the Prometheus in docker-compose
  prometheus:
    endpoint: 0.0.0.0:8889
    namespace: {service_name}
    const_labels:
      collector: otel

  # OTLP over gRPC — point this at your tracing backend
  # (Jaeger, Tempo, Datadog, Honeycomb, Grafana Cloud, etc.)
  otlp/tracing:
    endpoint: CHANGEME-traces-endpoint:4317
    tls:
      insecure: true  # set to false in production

  # Local file exporter for debugging
  file:
    path: /tmp/otel-debug.json

  # stdout for local development
  debug:
    verbosity: normal

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [otlp/tracing, debug]

    metrics:
      receivers: [otlp, prometheus]
      processors: [memory_limiter, resource, batch]
      exporters: [prometheus, debug]

    logs:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [debug]

  telemetry:
    logs:
      level: info
    metrics:
      level: detailed
      address: 0.0.0.0:8888
"""


_OTEL_PYTHON_DOC = """# OpenTelemetry instrumentation — Python / FastAPI

## 1. Install dependencies

```bash
pip install \\
    opentelemetry-api \\
    opentelemetry-sdk \\
    opentelemetry-instrumentation-fastapi \\
    opentelemetry-instrumentation-sqlalchemy \\
    opentelemetry-instrumentation-requests \\
    opentelemetry-instrumentation-logging \\
    opentelemetry-exporter-otlp-proto-grpc \\
    prometheus-fastapi-instrumentator
```

## 2. Wire it up in your app factory

```python
# backend/app/observability.py
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from prometheus_fastapi_instrumentator import Instrumentator


def configure_observability(app, service_name: str, environment: str):
    resource = Resource.create({
        "service.name": service_name,
        "deployment.environment": environment,
    })

    # Tracing
    trace.set_tracer_provider(TracerProvider(resource=resource))
    trace.get_tracer_provider().add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint="otel-collector:4317", insecure=True)
        )
    )

    # Metrics
    metrics.set_meter_provider(
        MeterProvider(
            resource=resource,
            metric_readers=[
                PeriodicExportingMetricReader(
                    OTLPMetricExporter(endpoint="otel-collector:4317", insecure=True)
                )
            ],
        )
    )

    # Auto-instrumentation
    FastAPIInstrumentor().instrument_app(app)
    SQLAlchemyInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    LoggingInstrumentor().instrument(set_logging_format=True)

    # Prometheus /metrics endpoint on the app
    Instrumentator().instrument(app).expose(
        app, endpoint="/metrics", include_in_schema=False, tags=["observability"]
    )
```

Then in your `main.py`:

```python
from .observability import configure_observability

configure_observability(app, service_name="{service_name}", environment="dev")
```

## 3. Verify locally

```bash
docker-compose -f docker-compose.observability.yml up -d
curl http://localhost:YOUR-SERVICE-PORT/metrics | head -20
curl http://localhost:9090/targets  # Prometheus should list your service as UP
```

Open Grafana at http://localhost:3000 (admin / admin) and import
`grafana/dashboards/service_overview.json`.

## 4. Manual spans (when you need them)

Auto-instrumentation covers 80% of use cases. For critical business
operations, add manual spans:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

def process_payment(order_id: str):
    with tracer.start_as_current_span("process_payment") as span:
        span.set_attribute("order.id", order_id)
        try:
            result = run_payment(order_id)
            span.set_attribute("payment.status", result.status)
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            raise
```

## 5. Custom metrics

```python
from opentelemetry import metrics

meter = metrics.get_meter(__name__)
order_counter = meter.create_counter("orders_processed_total")
order_value = meter.create_histogram("order_value_usd")

def on_order_completed(order):
    order_counter.add(1, {"status": order.status})
    order_value.record(order.total_usd, {"currency": "USD"})
```
"""


_OTEL_DOTNET_DOC = """# OpenTelemetry instrumentation — .NET / ASP.NET Core

## 1. Install NuGet packages

```bash
dotnet add package OpenTelemetry
dotnet add package OpenTelemetry.Extensions.Hosting
dotnet add package OpenTelemetry.Exporter.OpenTelemetryProtocol
dotnet add package OpenTelemetry.Instrumentation.AspNetCore
dotnet add package OpenTelemetry.Instrumentation.Http
dotnet add package OpenTelemetry.Instrumentation.SqlClient
dotnet add package prometheus-net.AspNetCore
```

## 2. Wire it up in Program.cs

```csharp
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using OpenTelemetry.Metrics;
using Prometheus;

var builder = WebApplication.CreateBuilder(args);

var serviceName = "{service_name}";
var environment = builder.Environment.EnvironmentName;

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r
        .AddService(serviceName)
        .AddAttributes(new Dictionary<string, object>
        {
            ["deployment.environment"] = environment,
        }))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddHttpClientInstrumentation()
        .AddSqlClientInstrumentation(o =>
        {
            o.SetDbStatementForText = true;
        })
        .AddOtlpExporter(o =>
        {
            o.Endpoint = new Uri("http://otel-collector:4317");
        }))
    .WithMetrics(m => m
        .AddAspNetCoreInstrumentation()
        .AddHttpClientInstrumentation()
        .AddRuntimeInstrumentation()
        .AddOtlpExporter(o =>
        {
            o.Endpoint = new Uri("http://otel-collector:4317");
        }));

var app = builder.Build();

// Prometheus /metrics endpoint
app.UseRouting();
app.UseHttpMetrics();
app.MapMetrics();

app.MapControllers();

app.Run();
```

## 3. Verify locally

```bash
docker-compose -f docker-compose.observability.yml up -d
curl http://localhost:YOUR-SERVICE-PORT/metrics | head -20
```

## 4. Manual spans

```csharp
using System.Diagnostics;

public class OrderService
{
    private static readonly ActivitySource ActivitySource = new("{service_name}.OrderService");

    public async Task<OrderResult> ProcessAsync(string orderId)
    {
        using var activity = ActivitySource.StartActivity("ProcessOrder");
        activity?.SetTag("order.id", orderId);

        try
        {
            var result = await DoWorkAsync(orderId);
            activity?.SetTag("order.status", result.Status);
            return result;
        }
        catch (Exception ex)
        {
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            activity?.RecordException(ex);
            throw;
        }
    }
}
```

Register the ActivitySource in your TracerProvider config
(`AddSource("{service_name}.OrderService")` during WithTracing).
"""


# ── Runbooks ───────────────────────────────────────────────────────────────


_RUNBOOK_HIGH_LATENCY = """# Runbook — High latency

**Alert name**: `{service_name_alert}HighLatencyP99`
**SLO impact**: api-latency-p99 (99%% under 500ms)
**Severity**: warning (auto-escalates to page after 15 min)

## Symptoms

- Grafana dashboard `{service_name} — service overview` shows p99
  latency above 500ms (yellow) or 1000ms (red)
- User reports of slow responses
- Downstream services timing out on calls to this one

## Diagnosis checklist

Work through these in order. Stop as soon as one answers "yes".

### 1. Is it a traffic spike?
- Check the request rate panel. Compare current rate to the same
  hour yesterday and last week.
- If current rate is >2x baseline, this is a capacity problem, not
  a code problem. Scale horizontally (more replicas) or vertically
  (bigger instances).

### 2. Is a downstream dependency slow?
- Check the traces for the slowest endpoint.
- Look for spans that dominate the request duration.
- Common culprits: database queries, external API calls, cache
  misses.
- If a specific downstream is slow, pivot to that service's
  runbook.

### 3. Is it a recent deploy?
- Check the deployment timeline (Grafana annotations or CI/CD).
- If a deploy landed within the last 2 hours, consider rollback
  as the first action.

### 4. Is it a specific endpoint?
- Filter the latency panel by route.
- If one endpoint dominates, look at recent commits touching its
  handler.

### 5. Is it a database issue?
- Check connection pool saturation.
- Check slow query log.
- Check replication lag on read replicas.

## Mitigation

1. **If it is a traffic spike**: scale up horizontally. Most
   platforms (K8s HPA, ECS auto-scaling) should have done this
   already — verify the HPA is not stuck at max replicas.

2. **If it is a code regression**: rollback the most recent
   deploy. Open a P2 ticket to investigate after the service is
   stable.

3. **If it is a database issue**: kill long-running queries,
   increase connection pool size, or fail over to a read replica
   for read-heavy workloads.

4. **If it is a downstream dependency**: implement a circuit
   breaker or increase timeout budgets temporarily. Escalate to
   the owning team.

## Escalation

- 15 minutes without resolution → page the on-call lead
- 1 hour without resolution → declare incident, create
  #incident-{service_name} channel
- Any customer-visible impact → notify comms team

## Postmortem

Write one within 48 hours. Cover:
- Timeline (alert → diagnosis → mitigation → resolution)
- Root cause
- What was the blast radius on the error budget?
- What would have made this easier to diagnose?
- Action items with owners
"""


_RUNBOOK_ERROR_BUDGET = """# Runbook — Error budget burn

**Alert name**: `{service_name_alert}ErrorBudgetBurnFast` or
`{service_name_alert}ErrorBudgetBurnSlow`
**SLO impact**: api-availability (99.9%% non-5xx)
**Severity**: fast = critical (page), slow = warning (ticket)

## Symptoms

- Grafana dashboard `{service_name} — error budget` shows remaining
  budget dropping rapidly
- 5xx rate panel is above 1%%
- Burn rate 1h or 6h is above 6x

## Diagnosis checklist

### 1. What is the status code distribution?
- Filter 5xx responses by specific status code.
- 500: unhandled exception in the service
- 502: upstream bad gateway — a dependency is returning garbage
- 503: service unavailable — possibly OOM or health check failing
- 504: gateway timeout — a dependency is slow

### 2. What are the error messages?
- Find the top 5 distinct error messages in the logs for the
  affected window.
- Use the trace ID from a failing request to pull the full trace.
- Is the error from the service code or from infrastructure?

### 3. Is it a deploy regression?
- Check the deployment timeline.
- If a deploy is within 2h of the burn starting, consider rollback.

### 4. Is it a dependency outage?
- Check the status pages of all external dependencies.
- Check the health of databases, caches, message queues.
- If a dep is down, pivot to its runbook or declare an incident.

### 5. Is it a traffic pattern change?
- Has a batch job or retry storm hit the service?
- Look for spikes in requests from a single client ID or IP range.
- Consider rate limiting the offending caller.

## Mitigation

Priority order:

1. **Rollback**: if a recent deploy is suspect, rollback within
   10 minutes of the alert. Do not try to fix forward during an
   active burn.

2. **Shed load**: if a traffic spike is the cause, enable rate
   limiting or circuit break the offending caller. Protect
   well-behaved traffic.

3. **Failover**: if a dependency is the cause, use the circuit
   breaker to fail open (degraded mode) rather than propagating
   errors.

4. **Scale**: if capacity is the cause, scale up. Only helps if
   the cluster has headroom.

## Budget accounting

After mitigation:

1. Calculate the budget consumed by this incident:
   `(incident_duration_seconds / 30_days_seconds) * error_rate`
2. Update the service's reliability dashboard.
3. If this incident consumed >20%% of the monthly budget, it is a
   P0 post-incident review.
4. If the remaining budget after the incident is <10%% with more
   than 7 days left in the window, initiate feature freeze and
   prioritize reliability work.

## Escalation

- Fast burn alert: immediate page on-call
- Slow burn alert: ticket during business hours
- Budget consumed >50%% in one incident: declare major incident,
  page management chain
- Budget exhausted: executive notification

## Postmortem

Required for any incident that consumed >10%% of the monthly
budget. Follow the standard postmortem template with an explicit
budget impact section.
"""


_RUNBOOK_TEMPLATE = """# Runbook — CHANGEME alert name

**Alert name**: `CHANGEME`
**SLO impact**: CHANGEME
**Severity**: CHANGEME

## Symptoms

- What the user sees
- What the dashboard shows
- What the logs say

## Diagnosis checklist

Write these in order of most-likely-to-least-likely, not by
system layer. The first item should catch 60%% of incidents, the
second 20%%, the third 10%%, etc.

### 1. CHANGEME first hypothesis

### 2. CHANGEME second hypothesis

### 3. CHANGEME third hypothesis

## Mitigation

List the actions in priority order. Most runbooks should lead
with "rollback the recent deploy" because that is the safest
action during an active incident.

1. CHANGEME
2. CHANGEME
3. CHANGEME

## Escalation

- CHANGEME triggers for the next on-call tier
- CHANGEME triggers for incident declaration
- CHANGEME triggers for comms team involvement

## Postmortem

When is a postmortem required for this alert? What are the
specific fields the postmortem must include (e.g. budget impact,
customer communication log)?
"""


# ── Docker Compose ─────────────────────────────────────────────────────────


_DOCKER_COMPOSE = """# Local observability stack — Prometheus + Grafana + OTel Collector
#
# Usage:
#   docker-compose -f docker-compose.observability.yml up -d
#   open http://localhost:3000  # Grafana (admin / admin)
#   open http://localhost:9090  # Prometheus
#
# The service being observed is NOT in this file. Run it
# separately on the host and point prometheus/prometheus.yml at
# its /metrics endpoint (the file has a CHANGEME-host placeholder).

services:
  prometheus:
    image: prom/prometheus:v2.51.0
    container_name: prometheus
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./prometheus/alerts.yml:/etc/prometheus/alerts.yml:ro
      - prometheus-data:/prometheus
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.path=/prometheus
      - --web.enable-lifecycle
    ports:
      - "9090:9090"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:10.4.0
    container_name: grafana
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/datasources:/etc/grafana/provisioning/datasources:ro
      - ./grafana/dashboards:/var/lib/grafana/dashboards:ro
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
    restart: unless-stopped

  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.98.0
    container_name: otel-collector
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel/collector-config.yaml:/etc/otel-collector-config.yaml:ro
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
      - "8889:8889"   # Prometheus metrics from collector
      - "8888:8888"   # Collector's own telemetry
    restart: unless-stopped

volumes:
  prometheus-data:
  grafana-data:
"""


# ── README ─────────────────────────────────────────────────────────────────


_README = """# Observability bootstrap bundle — {service_name}

Auto-generated by NexusForge. Drop this bundle next to your
service's source code to establish a production-ready observability
stack on day one. SLOs, alerts, dashboards, tracing, and runbooks —
all wired together.

## What is in this bundle

### SLO definitions (`slo/`)

- `api_latency.yaml` — p99 < 500ms, 99%% objective
- `api_availability.yaml` — non-5xx rate, 99.9%% objective
- `error_budget.md` — error budget math, burn rate policy, how to
  read the dashboards, when to trigger feature freeze

### Prometheus (`prometheus/`)

- `prometheus.yml` — scrape config for the service and the OTel
  collector. Has a CHANGEME-host placeholder for the service
  endpoint.
- `alerts.yml` — golden signals (latency, error rate) plus
  multi-window multi-burn-rate error budget alerts following the
  Google SRE workbook pattern

### Grafana (`grafana/`)

- `dashboards/service_overview.json` — four-panel golden signals
  dashboard (rate / latency / errors / saturation)
- `dashboards/error_budget.json` — SLO-focused: availability stat,
  error budget gauge, burn rate time series
- `datasources/prometheus.yml` — Grafana provisioning config

### OpenTelemetry (`otel/`)

- `collector-config.yaml` — full OTel Collector pipeline covering
  traces + metrics + logs. Point the exporters at your chosen
  backend (Jaeger, Tempo, Datadog, Honeycomb, Grafana Cloud).
- `instrumentation-python.md` — FastAPI setup walkthrough
- `instrumentation-dotnet.md` — ASP.NET Core setup walkthrough

### Runbooks (`runbooks/`)

- `high_latency.md` — step-by-step diagnosis and mitigation for
  the p99 latency alert
- `error_budget_burn.md` — step-by-step for the SLO budget burn
  alerts (both fast and slow burn)
- `template.md` — blank runbook for any new alerts

### Local stack (`docker-compose.observability.yml`)

Spins up Prometheus + Grafana + OTel Collector on localhost for
testing instrumentation before pushing. Run `docker-compose -f
docker-compose.observability.yml up -d` and open
http://localhost:3000 (admin / admin).

## What you still need to do

1. **Replace every `CHANGEME` placeholder**. Grep the bundle for
   the word CHANGEME to see them all. At minimum: service hostname
   + port in `prometheus/prometheus.yml` and `otel/collector-config.yaml`,
   environment label in both, team owner in `slo/*.yaml`, and
   tracing backend endpoint in `otel/collector-config.yaml`.

2. **Import the Grafana dashboards**. Grafana will auto-load them
   if the provisioning datasource is set up, but the first time you
   connect, verify they show up and that data is flowing.

3. **Instrument the service** using the Python or .NET guide. This
   is the only step that requires code changes.

4. **Set up alertmanager** (not included in the bundle — it is
   assumed you already have one). Point the `alerting.alertmanagers`
   block in `prometheus/prometheus.yml` at your alertmanager
   instance.

5. **Wire runbooks to alert annotations**. Every alert in
   `alerts.yml` has a `runbook_url` annotation — point it at wherever
   you host the runbooks in production (Confluence, Notion, a URL
   under docs.your-company.com, etc.).

6. **Tune the SLO objectives**. The generated values (99%% for
   latency, 99.9%% for availability) are reasonable defaults for a
   tier-1 service but may be too strict or too loose for your case.
   Read `slo/error_budget.md` before changing them.

## Why these specific alerts

The multi-window multi-burn-rate pattern (2%% budget in 1h + 5%%
budget in 6h) is chosen deliberately:

- **Fast window** catches acute incidents within minutes. Pages
  on-call.
- **Slow window** catches gradual regressions that accumulate
  over hours. Tickets during business hours.
- **The AND between windows** prevents flapping from transient
  spikes. A 30-second error burst does not page anyone.

Avoid the trap of alerting on "error rate above X%%" as a single
threshold — it either fires constantly (X too low) or too late
(X too high). The burn rate pattern aligns alert urgency with
actual budget impact.

_Generated by NexusForge observability bootstrapper. Not real
client data. Replace all CHANGEME placeholders before using in
a real service._
"""


# ── Public entry point ─────────────────────────────────────────────────────


def generate_observability_bundle(
    out_dir: Path,
    service_name: str = "my-service",
) -> GeneratedObservability:
    """Write the full observability bundle to out_dir.

    Args:
        out_dir: Target directory. Created if it does not exist.
        service_name: Logical name of the service being observed.
            Used as the Prometheus job name, the OTel resource
            service.name, the Grafana dashboard title prefix, and
            the prefix of alert names (`ServiceHighLatencyP99` etc.).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Alert name safe form — strip dashes/dots for PromQL labels
    safe_name = "".join(
        part.capitalize() for part in service_name.replace(".", "-").split("-") if part
    ) or "Service"

    # Sub-directories
    slo_dir = out_dir / "slo"
    prom_dir = out_dir / "prometheus"
    grafana_dash = out_dir / "grafana" / "dashboards"
    grafana_ds = out_dir / "grafana" / "datasources"
    otel_dir = out_dir / "otel"
    runbook_dir = out_dir / "runbooks"
    for d in (slo_dir, prom_dir, grafana_dash, grafana_ds, otel_dir, runbook_dir):
        d.mkdir(parents=True, exist_ok=True)

    result = GeneratedObservability(
        out_dir=str(out_dir),
        service_name=service_name,
    )

    def write(path: Path, content: str, kind: str = "") -> None:
        path.write_text(content, encoding="utf-8")
        rel = str(path.relative_to(out_dir)).replace("\\", "/")
        result.files_written.append(rel)
        if kind == "slo":
            result.slos_generated += 1
        elif kind == "dashboard":
            result.dashboards_generated += 1
        elif kind == "runbook":
            result.runbooks_generated += 1

    # SLOs
    write(
        slo_dir / "api_latency.yaml",
        _SLO_LATENCY_TEMPLATE.format(service_name=service_name),
        "slo",
    )
    write(
        slo_dir / "api_availability.yaml",
        _SLO_AVAILABILITY_TEMPLATE.format(service_name=service_name),
        "slo",
    )
    write(slo_dir / "error_budget.md", _ERROR_BUDGET_DOC)

    # Prometheus
    write(
        prom_dir / "prometheus.yml",
        _PROMETHEUS_YML.format(service_name=service_name),
    )
    write(
        prom_dir / "alerts.yml",
        _PROMETHEUS_ALERTS.format(
            service_name=service_name,
            service_name_alert=safe_name,
        ),
    )

    # Grafana
    write(
        grafana_dash / "service_overview.json",
        json.dumps(_service_overview_dashboard(service_name), indent=2),
        "dashboard",
    )
    write(
        grafana_dash / "error_budget.json",
        json.dumps(_error_budget_dashboard(service_name), indent=2),
        "dashboard",
    )
    write(grafana_ds / "prometheus.yml", _GRAFANA_DATASOURCE)

    # OTel — use str.replace() for the docs because their code examples
    # contain literal `{...}` braces that .format() would misinterpret.
    write(
        otel_dir / "collector-config.yaml",
        _OTEL_COLLECTOR_CONFIG.replace("{service_name}", service_name),
    )
    write(
        otel_dir / "instrumentation-python.md",
        _OTEL_PYTHON_DOC.replace("{service_name}", service_name),
    )
    write(
        otel_dir / "instrumentation-dotnet.md",
        _OTEL_DOTNET_DOC.replace("{service_name}", service_name),
    )

    # Runbooks
    write(
        runbook_dir / "high_latency.md",
        _RUNBOOK_HIGH_LATENCY.format(
            service_name=service_name, service_name_alert=safe_name
        ),
        "runbook",
    )
    write(
        runbook_dir / "error_budget_burn.md",
        _RUNBOOK_ERROR_BUDGET.format(
            service_name=service_name, service_name_alert=safe_name
        ),
        "runbook",
    )
    write(runbook_dir / "template.md", _RUNBOOK_TEMPLATE, "runbook")

    # Docker compose + README
    write(out_dir / "docker-compose.observability.yml", _DOCKER_COMPOSE)
    write(out_dir / "README.md", _README.format(service_name=service_name))

    return result
