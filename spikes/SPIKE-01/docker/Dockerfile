# Offline-build image for SPIKE-01 tier 2. Built WITH network (stands in for the platform's
# toolchain mirror step); every build/run of a project uses --network none.
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      git curl ca-certificates xz-utils zstd libgmp10 && rm -rf /var/lib/apt/lists/*
ENV ELAN_HOME=/opt/elan PATH=/opt/elan/bin:$PATH
RUN curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh \
      | sh -s -- -y --default-toolchain none
ARG TOOLCHAINS="leanprover/lean4:v4.32.0"
RUN for t in $TOOLCHAINS; do elan toolchain install "$t"; done
WORKDIR /work
