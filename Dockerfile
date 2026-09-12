FROM python:3.14-alpine

WORKDIR /app

RUN apk add --no-cache \
    openssl \
    postgresql17-client

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

COPY src ./src
COPY alembic.ini .
COPY entrypoint.sh .
COPY manage_tenants.py .
COPY generateFakeData.py .

RUN chmod +x entrypoint.sh

EXPOSE 8000
CMD ["./entrypoint.sh"]
