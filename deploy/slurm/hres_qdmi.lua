-- Copyright (c) 2026 Munich Quantum Software Company GmbH
-- All rights reserved.
--
-- SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
--
-- Licensed under the Apache License v2.0 with LLVM Exceptions.
-- See https://llvm.org/LICENSE.txt for license information.

local function quote(value)
    return "'" .. (tostring(value):gsub("'", "'\\''")) .. "'"
end

function hres_create_context(ctx, layers)
    -- Admission starts closed on startup and reconfiguration.
    return slurm.ESLURM_HRES_MAINTENANCE_DISABLE
end

-- Only these fixed probe reasons reach the log, never provider output.
local REASONS = {
    idle = true, busy = true, offline = true, error = true, maintenance = true,
    calibration = true, unregistered = true, unavailable = true,
}
local last_reason -- This maintenance state belongs to one resource.

function hres_maintenance(ctx, layers)
    -- Slurm's maintenance_timeout only logs slow calls; timeout enforces the bound.
    local probe = io.popen(string.format(
        "/usr/bin/timeout --kill-after=2s 10s /usr/local/libexec/mqt-qdmi-probe %s </dev/null 2>/dev/null",
        quote(ctx.name)))
    local reason
    for line in probe:lines() do reason = line end
    local succeeded, _, code = probe:close()
    if code == 124 or code == 137 then
        reason = "timeout"
    elseif not REASONS[reason] then
        reason = "failed"
    end
    local available = succeeded == true and (reason == "idle" or reason == "busy")
    for _, layer in ipairs(layers) do layer.disable_layer = not available end
    if reason ~= last_reason then
        slurm.log_info("hres_qdmi: %s admission %s: %s", ctx.name, available and "open" or "closed", reason)
        last_reason = reason
    end
    return slurm.SUCCESS
end

-- Remote sessions belong to the application; HRES accounts for cluster capacity.
local function success() return slurm.SUCCESS end
hres_destroy_context = success
hres_controller_job_prerun, hres_controller_job_revoke = success, success
hres_controller_job_epilog = success
hres_node_job_prolog, hres_node_job_epilog = success, success
hres_node_task_prolog, hres_node_task_epilog = success, success
hres_node_user_task_prolog = success
