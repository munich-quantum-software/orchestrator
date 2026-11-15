# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

FROM ghcr.io/astral-sh/uv:0.13.5 AS uv

FROM ubuntu:26.04 AS python

ENV UV_PYTHON_INSTALL_DIR=/opt/python \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH
RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=uv /uv /uvx /bin/
ARG UV_LINK_MODE=copy
ARG UV_PYTHON_CACHE_DIR=/root/.cache/uv/python
RUN --mount=type=cache,target=/root/.cache/uv \
    uv python install 3.14 --compile-bytecode \
    && uv venv --python 3.14 /opt/venv

FROM python AS build-tools

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        build-essential clang lld cmake curl git libcurl4-openssl-dev libssl-dev zstd \
    && rm -rf /var/lib/apt/lists/*
ARG CMAKE_BUILD_PARALLEL_LEVEL=2

FROM build-tools AS native

RUN apt-get update \
    && apt-get install --no-install-recommends -y ninja-build pkg-config \
        libglib2.0-dev liblz4-dev zlib1g-dev libdbus-1-dev libhwloc-dev libjson-c-dev \
        liblua5.4-dev libmariadb-dev libmunge-dev libpam0g-dev libpmix-dev libreadline-dev libyaml-dev \
    && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/spack/spack.git /opt/spack \
    && git -C /opt/spack checkout 2ad33296baf6392fb183dd49f1ebffa1e0b9c1ec
ENV PATH=/opt/spack/bin:$PATH SPACK_USER_CONFIG_PATH=/opt/spack-config
RUN mkdir -p /tmp/setup-mlir \
    && curl -fLsS https://github.com/munich-quantum-software/setup-mlir/archive/246aa0c70414109aa55fa19a5370739519833512.tar.gz \
        | tar -xz -C /tmp/setup-mlir --strip-components=1 \
    && bash /tmp/setup-mlir/installation/setup-mlir.sh -v 23.1.4 -p /opt/llvm -a OFF \
    && rm -rf /tmp/setup-mlir
COPY --from=orchestrator pyproject.toml uv.lock /opt/build-workspace/
COPY --from=orchestrator demos/qc-afqmc/pyproject.toml /opt/build-workspace/demos/qc-afqmc/pyproject.toml
RUN --mount=type=cache,target=/root/.cache/uv \
    UV_PROJECT_ENVIRONMENT=/opt/venv uv sync --project /opt/build-workspace --frozen --only-group native-build

COPY --from=orchestrator deploy/spack/spack.yaml deploy/spack/configure.py /opt/mqsc-environment/
COPY --from=orchestrator deploy/spack/spack_repo /opt/mqsc-environment/spack_repo
RUN --mount=type=cache,target=/root/.spack \
    --mount=type=cache,target=/opt/spack/opt \
    python /opt/mqsc-environment/configure.py \
    && spack -e /opt/mqsc-environment compiler find /usr/bin \
    && spack -e /opt/mqsc-environment external find --not-buildable cmake gmake ninja curl openssl \
    && spack -e /opt/mqsc-environment concretize \
    && spack -e /opt/mqsc-environment install --show-log-on-error -j4 \
    && test -f /opt/mqsc-environment/view/lib/slurm/hres_lua.so \
    && mkdir -p /opt/native-store \
    && spack -e /opt/mqsc-environment find --format '{prefix}' | while read -r prefix; do \
        case "$prefix" in /opt/spack/opt/*) cp -a --parents "$prefix" /opt/native-store ;; esac; \
    done

FROM build-tools AS environment

COPY --from=native /opt/native-store/opt/spack/opt /opt/spack/opt
COPY --from=native /opt/mqsc-environment /opt/mqsc-environment
COPY --from=orchestrator pyproject.toml uv.lock /opt/workspace/
COPY --from=orchestrator demos/qc-afqmc/pyproject.toml /opt/workspace/demos/qc-afqmc/pyproject.toml
RUN --mount=type=cache,target=/root/.cache/uv \
    UV_PROJECT_ENVIRONMENT=/opt/venv uv sync --project /opt/workspace --frozen --all-packages --no-dev \
        --no-install-package mqt-core

FROM python AS runtime

ENV container=docker PATH=/opt/venv/bin:/opt/slurm/bin:/opt/slurm/sbin:$PATH
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
        libcurl4t64 dbus munge systemd libhwloc15 libjson-c5 liblua5.4-0 \
        openmpi-bin libmariadb3 libnuma1 libopenmpi40 libpmix2t64 libreadline8t64 libyaml-0-2 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=native /opt/native-store/opt/spack/opt /opt/spack/opt
COPY --from=native /opt/mqsc-environment /opt/mqsc-environment
RUN ln -s /opt/mqsc-environment/view /opt/slurm \
    && cp /opt/slurm/lib/systemd/system/*.service /etc/systemd/system/
COPY --from=environment /opt/venv /opt/venv
RUN printf '%s\n' '/opt/slurm/lib/python3.14/site-packages' > /opt/venv/lib/python3.14/site-packages/spack.pth
COPY --chmod=755 start.sh /usr/local/sbin/mqt-slurm-start
COPY --chmod=755 probe.py /usr/local/libexec/mqt-qdmi-probe
COPY hres_qdmi.lua /etc/slurm/hres_qdmi.lua
COPY slurmctld.conf /etc/systemd/system/slurmctld.service.d/qdmi.conf
COPY slurm-accounting.service /etc/systemd/system/
COPY --chmod=755 accounting.sh /usr/local/sbin/mqt-slurm-accounting
COPY node.conf slurmdbd.conf /usr/local/share/mqt-slurm/
COPY profile.sh /etc/profile.d/mqt-qdmi.sh
RUN useradd --uid 10000 --user-group --create-home mqt-dev \
    && useradd --system --user-group --home-dir /var/lib/slurm slurm \
    && systemctl disable slurmctld.service slurmd.service slurmdbd.service

STOPSIGNAL SIGRTMIN+3
CMD ["/usr/local/sbin/mqt-slurm-start", "node"]
