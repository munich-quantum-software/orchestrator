#!/bin/sh
# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

set -eu

cluster=$(sacctmgr --noheader --parsable2 show cluster mqsc-orchestrator format=Cluster)
if [ -z "$cluster" ]; then
    sacctmgr --immediate add cluster mqsc-orchestrator
fi
account=$(sacctmgr --noheader --parsable2 show account research format=Account)
if [ -z "$account" ]; then
    sacctmgr --immediate add account research Description="QDMI workloads" Organization=MQT
fi
association=$(sacctmgr --noheader --parsable2 show association where Cluster=mqsc-orchestrator Account=research User=mqt-dev format=User)
if [ -z "$association" ]; then
    sacctmgr --immediate add user mqt-dev Cluster=mqsc-orchestrator Account=research DefaultAccount=research
fi
