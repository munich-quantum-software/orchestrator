# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

"""Documentation for the MQSC reference deployment."""

project = "MQSC Orchestrator"
author = "Munich Quantum Software Company GmbH"
copyright = "2026, Munich Quantum Software Company GmbH"
extensions = [
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx.ext.intersphinx",
    "sphinx.ext.extlinks",
    "sphinxext.opengraph",
]
html_theme = "furo"
html_title = "MQSC Orchestrator"
html_static_path = ["_static"]
html_css_files = ["orchestrator.css"]
html_js_files = ["workflow.js"]
exclude_patterns = ["_build"]
myst_heading_anchors = 3
myst_enable_extensions = ["colon_fence", "deflist"]
html_favicon = "_static/orchestrator-icon.svg"
html_context = {"default_mode": "light"}

html_theme_options = {
    "light_logo": "orchestrator-light.svg",
    "dark_logo": "orchestrator-dark.svg",
    "source_repository": "https://github.com/munich-quantum-software/orchestrator/",
    "source_branch": "main",
    "source_directory": "docs/",
    "navigation_with_keys": True,
    "sidebar_hide_name": True,
    "light_css_variables": {"color-brand-primary": "#3070b3", "color-brand-content": "#245a92"},
    "dark_css_variables": {"color-brand-primary": "#8abcef", "color-brand-content": "#8abcef"},
}
html_show_sourcelink = True
nitpicky = True

html_baseurl = "https://mqsc-orchestrator.readthedocs.io/en/latest/"
ogp_site_url = html_baseurl
extlinks = {"issue": ("https://github.com/munich-quantum-software/orchestrator/issues/%s", "#%s")}
