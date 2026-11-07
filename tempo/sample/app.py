import time
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/trace-test", methods=["GET"])
def trace_test():
    """
    분산 추적(Trace) 테스트 엔드포인트
    - 여러 외부 퍼블릭 API를 순차적으로 호출하여 구간별 지연(Latency) 및 병목 지점을 확인합니다.
    - 쿼리 파라미터:
      - delay: HTTPBin 병목 시뮬레이션 지연 시간(초, 기본값: 1.0)
      - include_delay: 의도적 지연 API 포함 여부 ('true'/'false', 기본값: 'true')
    """
    delay_param = request.args.get("delay", default="1.0")
    try:
        delay = float(delay_param)
    except ValueError:
        delay = 1.0

    include_delay = request.args.get("include_delay", default="true").lower() in ("true", "1", "yes")

    # 신뢰성이 높고 잘 변하지 않는 공개 퍼블릭 API 목록
    targets = [
        {
            "name": "Cloudflare CDN Trace",
            "description": "Cloudflare 전세계 엣지 진단 API (초저지연 기대)",
            "url": "https://1.1.1.1/cdn-cgi/trace",
            "headers": {"User-Agent": "Flask-Trace-Test"},
            "timeout": 5.0,
        },
        {
            "name": "GitHub Zen",
            "description": "GitHub 공용 엔드포인트 (안정적인 글로벌 API)",
            "url": "https://api.github.com/zen",
            "headers": {"User-Agent": "Flask-Trace-Test"},
            "timeout": 5.0,
        },
        {
            "name": "JSONPlaceholder Post",
            "description": "Mock REST API (전형적인 외부 JSON API 응답)",
            "url": "https://jsonplaceholder.typicode.com/posts/1",
            "headers": {"User-Agent": "Flask-Trace-Test"},
            "timeout": 5.0,
        },
        {
            "name": "Open-Meteo Weather",
            "description": "무료 기상 오픈 API (실시간 데이터 연산/제공)",
            "url": "https://api.open-meteo.com/v1/forecast?latitude=37.5665&longitude=126.9780&current_weather=true",
            "headers": {"User-Agent": "Flask-Trace-Test"},
            "timeout": 5.0,
        },
    ]

    # 병목 지점 시뮬레이션용 지연 API (선택적)
    if include_delay and delay > 0:
        targets.append({
            "name": f"HTTPBin Delay ({delay}s simulation)",
            "description": "인위적 응답 지연을 발생시켜 Trace 상의 병목을 시뮬레이션",
            "url": f"https://httpbin.org/delay/{delay}",
            "headers": {"User-Agent": "Flask-Trace-Test"},
            "timeout": delay + 5.0,
        })

    results = []
    total_start = time.perf_counter()

    for target in targets:
        step_start = time.perf_counter()
        call_info = {
            "name": target["name"],
            "description": target["description"],
            "url": target["url"],
            "status": "success",
            "status_code": None,
            "duration_ms": 0.0,
            "response_snippet": None,
            "error": None,
        }

        try:
            resp = requests.get(
                target["url"],
                headers=target.get("headers"),
                timeout=target.get("timeout", 5.0),
            )
            call_info["status_code"] = resp.status_code
            call_info["duration_ms"] = round((time.perf_counter() - step_start) * 1000, 2)

            # 응답 요약 (너무 길지 않게 한 줄로 압축)
            text_preview = " ".join(resp.text.strip().split())
            call_info["response_snippet"] = (
                text_preview[:120] + "..." if len(text_preview) > 120 else text_preview
            )

            if not resp.ok:
                call_info["status"] = "http_error"

        except Exception as exc:
            call_info["status"] = "failed"
            call_info["duration_ms"] = round((time.perf_counter() - step_start) * 1000, 2)
            call_info["error"] = str(exc)

        results.append(call_info)

    total_duration_ms = round((time.perf_counter() - total_start) * 1000, 2)

    # 병목 지점(가장 오래 걸린 호출) 분석
    slowest_call = max(results, key=lambda x: x["duration_ms"]) if results else None

    return jsonify({
        "message": "Trace test completed",
        "total_duration_ms": total_duration_ms,
        "bottleneck": {
            "name": slowest_call["name"] if slowest_call else None,
            "duration_ms": slowest_call["duration_ms"] if slowest_call else 0.0,
            "percentage": round((slowest_call["duration_ms"] / total_duration_ms * 100), 1) if (slowest_call and total_duration_ms > 0) else 0.0,
        },
        "calls": results,
    })

if __name__ == '__main__':
    app.run(host="0.0.0.0", port="5000", debug=True)

