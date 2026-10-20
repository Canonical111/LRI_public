# Optional raw-replay environment recipe. The image build was not executed here.
FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libgmp-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /project
COPY requirements.txt requirements-raw.txt /project/
RUN python -m pip install --no-cache-dir -r requirements-raw.txt
# Run with -v "$PWD":/project -v "$PWD/work":/mnt/data.
CMD ["python", "run_checks.py", "--skip-hashes"]
