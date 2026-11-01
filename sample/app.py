import logging
import random
import time
from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# 1. OpenTelemetry 분산 트레이서 설정 (Tempo OTLP gRPC 엔드포인트 연동)
resource = Resource(attributes={"service.name": "python-telemetry-app"})
provider = TracerProvider(resource=resource)
otlp_exporter = OTLPSpanExporter(
    endpoint="tempo.monitoring.svc.cluster.local:4317",
    insecure=True
)
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
trace.set_tracer_provider(provider)

# 2. 로깅 포맷에 Trace ID와 Span ID를 주입하는 필터 구성
class TraceIdFilter(logging.Filter):
    def filter(self, record):
        span = trace.get_current_span()
        span_ctx = span.get_span_context() if span else None
        if span_ctx and span_ctx.is_valid:
            record.trace_id = format(span_ctx.trace_id, "032x")
            record.span_id = format(span_ctx.span_id, "016x")
        else:
            record.trace_id = "0" * 32
            record.span_id = "0" * 16
        return True

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "trace_id": "%(trace_id)s", "span_id": "%(span_id)s", "message": "%(message)s"}'
    )
)
logger.addFilter(TraceIdFilter())
logger.addHandler(handler)

# 3. FastAPI 인스턴스 생성 및 자동 계측
app = FastAPI()

# Prometheus 메트릭 엔드포인트(/metrics) 활성화
Instrumentator().instrument(app).expose(app)

# FastAPI HTTP 요청 자동 트레이싱 등록
FastAPIInstrumentor.instrument_app(app)

# 4. 테스트용 엔드포인트 정의
@app.get("/")
def get_root():
    logger.info("Successfully processed root request")
    return {"status": "ok", "service": "python-telemetry-app"}

@app.get("/slow")
def get_slow():
    delay = random.uniform(0.4, 1.2)
    time.sleep(delay)
    logger.info(f"Slow transaction finished with delay: {delay:.2f}s")
    return {"status": "delayed", "duration_sec": delay}

@app.get("/error")
def get_error():
    logger.error("Internal processing failed at /error endpoint")
    raise HTTPException(status_code=500, detail="Sample Internal Server Error")

