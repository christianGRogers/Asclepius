# One image, two roles: the API server and the background worker. They share
# every dependency and differ only in their command, so building them separately
# would mean two things to keep in step for no benefit.
#
# Python 3.11 because Girder 5 requires >= 3.10. (The Slicer extension is stuck
# on 3.9 and shares code with this image through src/segqueue, which is why that
# package is stdlib-only and 3.9-compatible.)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# libgomp is SimpleITK's only non-Python need; it arrives with the [scoring]
# extra and is what the QA worker uses to read submitted label volumes.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 curl \
 && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 girder

WORKDIR /repo
COPY pyproject.toml README.md ./
COPY src ./src
COPY server ./server

# The repository root first, then the plugin. Order matters: girder-segqueue
# deliberately does not declare `segqueue` as a dependency, because the
# distribution providing it is named `segtrain` and an unrelated project owns
# that name on PyPI. Installing the root here is what satisfies it.
RUN pip install . \
 && pip install "./server[scoring]"

# Girder writes uploads here through its filesystem assetstore, and the ingest
# CLI reads source volumes from it. Bind-mounted in compose so the data outlives
# any container.
RUN mkdir -p /data && chown girder:girder /data
VOLUME ["/data"]

USER girder
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS http://localhost:8080/api/v1/system/version || exit 1

CMD ["girder", "serve", "--mode", "production", "-H", "0.0.0.0", "-p", "8080"]
