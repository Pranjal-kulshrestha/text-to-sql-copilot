FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
COPY copilot ./copilot
RUN pip install --no-cache-dir . && python -m copilot.seed data/shop.db
EXPOSE 8000
CMD ["uvicorn", "copilot.api:app", "--host", "0.0.0.0", "--port", "8000"]
