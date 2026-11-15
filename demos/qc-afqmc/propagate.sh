#!/bin/bash
# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

#SBATCH --nodes=2
#SBATCH --ntasks=4
#SBATCH --ntasks-per-node=2
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=04:00:00
#SBATCH --partition=compute
#SBATCH --output=results/propagate-%j.out

set -euo pipefail
demo_dir=${MQSC_AFQMC_ROOT:-/workspace/demos/qc-afqmc}

export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1

if (( SLURM_NTASKS > 1 )); then
    mpirun --bind-to core python -m mpi4py "$demo_dir/run.py" --stage propagate --mpi --output "$1"
else
    srun python "$demo_dir/run.py" --stage propagate --workers "$SLURM_CPUS_PER_TASK" --output "$1"
fi
