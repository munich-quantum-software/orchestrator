#!/bin/sh
# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

set -eu
umask 077
runtime=${1:-"$(dirname "$0")/../../build/slurm"}
mkdir -p "$(dirname "$runtime")"
mkdir "$runtime"
head -c 1024 /dev/urandom > "$runtime/munge.key"
mkdir "$runtime/jobs"
chmod 1777 "$runtime/jobs"
for config in slurm.conf resources.yaml qdmi.json; do
    cp "$(dirname "$0")/$config" "$runtime/$config"
    chmod 644 "$runtime/$config"
done
touch "$runtime/qdmi.env"
for secret in accounting-password database-password; do
    od -An -N24 -tx1 /dev/urandom | tr -d ' \n' > "$runtime/$secret"
done
