# Reproducible environment for the Dark Patterns ABM paper.
#
# Build from the REPOSITORY ROOT (the build context must include backend/ and
# the replication package) so the model source is available to reproduce.py:
#
#   docker build -f paper/technology-in-society/replication-package/Dockerfile \
#       -t dark-patterns-abm .
#
# Run (writes results into the mounted host package directory):
#
#   docker run --rm \
#       -v "$(pwd)/paper/technology-in-society/replication-package/data:/app/paper/technology-in-society/replication-package/data" \
#       -v "$(pwd)/paper/technology-in-society/replication-package/figures:/app/paper/technology-in-society/replication-package/figures" \
#       dark-patterns-abm
#
FROM python:3.12.5-slim

# System libs needed by matplotlib for headless (Agg) PDF rendering.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libfreetype6 libpng16-16 \
    && rm -rf /var/lib/apt/lists/*

# Install pinned dependencies first (better layer caching).
COPY paper/technology-in-society/replication-package/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Mirror the repository layout so reproduce.py finds ../../../backend at runtime.
WORKDIR /app
COPY backend/app /app/backend/app
COPY paper/technology-in-society/replication-package /app/paper/technology-in-society/replication-package

WORKDIR /app/paper/technology-in-society/replication-package
CMD ["python", "reproduce.py"]
