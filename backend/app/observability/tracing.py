"""OpenTelemetry tracing setup for NexusForge."""
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource

def setup_tracing(service_name='nexusforge-backend'):
    resource = Resource.create({'service.name': service_name})
    provider = TracerProvider(resource=resource)
    # Console exporter for local dev (replace with OTLP for production)
    processor = SimpleSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)

tracer = None

def get_tracer():
    global tracer
    if tracer is None:
        tracer = setup_tracing()
    return tracer
