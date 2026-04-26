FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir ".[api]"
COPY config/ config/
COPY src/ src/
RUN mkdir -p data/results
ENV KMP_DUPLICATE_LIB_OK=TRUE \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    MKL_THREADING_LAYER=sequential \
    OPENBLAS_NUM_THREADS=1 \
    VECLIB_MAXIMUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    PORT=8080
EXPOSE 8080
CMD uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
