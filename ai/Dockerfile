FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NIDAN_AI_AUTH_MODE=dev

# The frozen backend contract is imported by nidan_ai.schemas; install it first.
COPY backend/pyproject.toml backend/Backend-Architecture-Implementation.md /app/backend/
COPY backend/app /app/backend/app
COPY ai/pyproject.toml ai/README.md /app/ai/
COPY ai/nidan_ai /app/ai/nidan_ai

RUN pip install --no-cache-dir --upgrade pip setuptools && \
    pip install --no-cache-dir /app/backend && \
    pip install --no-cache-dir /app/ai

ENTRYPOINT ["python", "-m", "nidan_ai.worker.run"]
CMD ["--scenario", "monsoon-60d", "--seed", "42", "--shadow"]
