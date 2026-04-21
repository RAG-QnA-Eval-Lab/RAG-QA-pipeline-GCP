FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir ".[api,ko]"
COPY config/ config/
COPY src/ src/
COPY data/eval/ data/eval/
RUN mkdir -p data/results
EXPOSE 8000
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
