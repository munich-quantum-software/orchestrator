#!/bin/bash
# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:30:00
#SBATCH --partition=quantum
#SBATCH --licenses=mqt.ddsim.default:1
#SBATCH --output=results/measure-%j.out

set -euo pipefail
demo_dir=${MQSC_AFQMC_ROOT:-/workspace/demos/qc-afqmc}

export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1

srun python "$demo_dir/run.py" --stage measure --output "results/$SLURM_JOB_ID" "$@"
