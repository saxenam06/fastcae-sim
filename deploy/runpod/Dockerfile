# The RunPod serverless worker's image (PLT-12): the GPU pipeline's environment, built from uv.lock, and the handler.
# The code is not in the image: each job checks out its git ref onto the network volume (handler.py), so a code change
# needs no rebuild. Rebuild only when uv.lock, this file or handler.py changes.
#
# Build from the repository's root:
#   docker build -f deploy/runpod/Dockerfile -t <registry>/zenryx-worker:<tag> .
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PYVISTA_OFF_SCREEN=true

# git for the checkout; procps for the guard (ps); the OpenGL/X libraries CadQuery's OCP, gmsh and VTK load; Xvfb for
# the pictures (pyvista) on a worker with no screen. The NVIDIA driver comes from the host; the CUDA libraries from the
# wheels (cupy's [ctk], nvmath's cuDSS).
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates git bash procps curl tini \
        libgl1 libglu1-mesa libegl1 libgomp1 libxrender1 libxext6 libsm6 libx11-6 libxcursor1 libxft2 libxinerama1 \
        libxi6 libxkbcommon0 libfontconfig1 libdbus-1-3 xvfb \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /usr/local/bin/uv

WORKDIR /build
COPY pyproject.toml uv.lock ./
# Every extra (the geometry, the GPU solve, the checks); the project itself comes from the checkout (PYTHONPATH).
# tetgen and pymeshlab are outside uv.lock on the laptop too (CLAUDE.md); runpod is the worker's SDK.
RUN uv python install 3.12 \
    && uv sync --frozen --all-extras --no-install-project \
    && uv pip install --python /opt/venv/bin/python tetgen pymeshlab runpod \
    && sha256sum uv.lock | cut -d' ' -f1 > /opt/uv.lock.sha256 \
    && rm -rf /root/.cache

COPY deploy/runpod/handler.py /opt/worker/handler.py
WORKDIR /opt/worker
# tini as PID 1 reaps the stages a run ends (the guard ends a tree; the handler is not an init)
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/opt/venv/bin/python", "-u", "/opt/worker/handler.py"]
