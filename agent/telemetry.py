"""
agent/telemetry.py -- configure OpenTelemetry for ADK agents.

Call setup_telemetry(service_name) once at the top of each agent.py,
before constructing the Agent. ADK will automatically emit spans for
every agent turn, LLM call, and tool invocation.

Traces are exported via OTLP gRPC to localhost:4317 by default (Jaeger).
Override with the OTEL_EXPORTER_OTLP_ENDPOINT environment variable.

Usage:
    from agent.telemetry import setup_telemetry
    setup_telemetry("patch_builder")
"""

import os
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry import trace


def setup_telemetry(service_name: str) -> None:
    """Configure OTLP tracing for an ADK agent.

    Args:
        service_name: Name shown in the Jaeger UI (e.g. "patch_builder").
    """
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

    resource = Resource.create({"service.name": service_name})
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
