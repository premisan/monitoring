# 경량화 및 보안을 위해 python slim 이미지 사용
FROM python:3.11-slim

# 표준 출력/에러 버퍼링 방지 및 바이트코드 생성 비활성화
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

# 작업 디렉토리 설정
WORKDIR /app

# 보안 모범 사례: root 권한 대신 실행할 비특권 사용자 생성
RUN addgroup --system appgroup && adduser --system --group appuser

# 의존성 파일 복사 및 설치 (캐싱 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 소스 코드 복사
COPY . .

# 소유권 변경 및 비특권 사용자로 전환
RUN chown -R appuser:appgroup /app
USER appuser

# 애플리케이션 포트 노출
EXPOSE 5000

# 애플리케이션 실행
CMD ["python", "app.py"]
