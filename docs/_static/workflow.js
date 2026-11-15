/*
 * Copyright (c) 2026 Munich Quantum Software Company GmbH
 * All rights reserved.
 *
 * SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
 *
 * Licensed under the Apache License v2.0 with LLVM Exceptions.
 * See https://llvm.org/LICENSE.txt for license information.
 */

"use strict";
document.addEventListener("DOMContentLoaded", () => {
  const [blue, navy, pale, cyan] = ["#2F70B8", "#142B45", "#E8F1FA", "#60B3CB"];
  const iconBodies = {
    circuit: `<path d="M6 29H94M6 51H94M6 73H94M63 29V51" fill="none" stroke="${navy}" stroke-width="2"/><rect x="22" y="17" width="23" height="23" rx="3" fill="${pale}" stroke="${blue}" stroke-width="2"/><path d="M28 22V35M39 22V35M28 28H39" stroke="${blue}" stroke-width="2"/><circle cx="63" cy="29" r="4" fill="${blue}"/><circle cx="63" cy="51" r="9" fill="white" stroke="${blue}" stroke-width="2"/><path d="M57 51H69M63 45V57" stroke="${blue}" stroke-width="2"/>`,
    molecule: `<ellipse cx="35" cy="47" rx="29" ry="34" transform="rotate(-25 35 47)" fill="${blue}" opacity=".12"/><ellipse cx="65" cy="47" rx="29" ry="34" transform="rotate(25 65 47)" fill="${cyan}" opacity=".2"/><path d="M33 52L67 39" stroke="${navy}" stroke-width="5"/><circle cx="33" cy="52" r="18" fill="${blue}"/><circle cx="67" cy="39" r="11" fill="${cyan}"/><circle cx="29" cy="47" r="4" fill="white" opacity=".7"/><circle cx="63" cy="34" r="4" fill="white" opacity=".7"/>`,
  };
  const icon = (name, x, y) =>
    `<g transform="translate(${x} ${y})" aria-hidden="true">${iconBodies[name]}</g>`;

  const descriptions = [
    "Prepare the molecular trial and shadow circuits.",
    "Acquire the HRES license, then compile for the allocated device.",
    "Execute through QDMI within the allocation. DDSIM is ideal simulation.",
    "After successful measurement, propagate classical walkers on the compute partition.",
  ];
  for (const root of document.querySelectorAll(".workflow")) {
    const svg = root.querySelector("svg");
    const labels = [
      "Prepare",
      "Allocate + compile",
      "QDMI execution",
      "Classical continuation",
    ];
    const icons = ["molecule", "circuit", "circuit", "molecule"];
    const narrow = window.matchMedia("(max-width: 600px)");
    function render() {
      const vertical = narrow.matches;
      svg.setAttribute("viewBox", vertical ? "0 0 250 750" : "0 0 900 180");
      svg.innerHTML =
        [0, 1, 2]
          .map((i) => {
            const route = vertical
              ? `M125 ${155 + i * 190}v25m-6-9 6 9 6-9`
              : `M${155 + i * 225} 60h70m-9-6 9 6-9 6`;
            return `<path d="${route}" fill="none" stroke="currentColor" stroke-width="2"/>`;
          })
          .join("") +
        labels
          .map((label, i) => {
            const x = vertical ? 75 : 35 + i * 225;
            const y = vertical ? 10 + i * 190 : 10;
            return `<g class="stage" data-index="${i}">${icon(icons[i], x, y)}<text x="${x + 50}" y="${y + 140}" text-anchor="middle" font-size="17">${label}</text></g>`;
          })
          .join("");
      show(step);
    }
    let step = 0;
    function show(next) {
      step = Math.max(0, Math.min(3, next));
      for (const el of svg.querySelectorAll(".stage"))
        el.classList.toggle("active", Number(el.dataset.index) === step);
      root.querySelector(".workflow-description").textContent =
        `${step + 1}/4 — ${descriptions[step]}`;
    }
    for (const button of root.querySelectorAll("button"))
      button.addEventListener("click", () =>
        show(step + Number(button.dataset.step)),
      );
    root.addEventListener("keydown", (event) => {
      if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
        event.preventDefault();
        event.stopPropagation();
        show(step + (event.key === "ArrowRight" ? 1 : -1));
      }
    });
    narrow.addEventListener("change", render);
    render();
  }
});
