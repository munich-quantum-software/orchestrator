# AI usage guidelines

AI tools can help explore an idea, implement a change, or explain a result. The
contributor remains responsible for what reaches this repository: understand the
code, check its behavior, and make the contribution useful to its reviewers.

## Core principles

### Human responsibility

Review generated code and public text before accepting or merging it. Verify
that it solves the stated problem and fits the surrounding deployment. Keep
credentials, private data, and unreleased material out of tools that are not
authorized to receive them. Check the rights and license of contributed code and
assets, including generated material.

Agents may implement changes and manage issue and pull request workflows within
an explicitly authorized scope. Actions outside that scope require fresh
authorization. Human maintainers decide what to accept, merge, and publish.

### Communication and authorization

AI assistance may be used for issue and pull request descriptions, comments, and
reviews within an authorized scope. Keep every public message accurate,
relevant, and useful; a human remains responsible for what is posted.

### Clear attribution

Disclose material AI assistance in the PR description. Every agent-authored or
agent-edited public text body must begin with this visible disclosure:

`🤖 *AI text below* 🤖`

This includes issue and PR descriptions, reviews, inline comments, and replies.
Titles are exempt. When editing human-authored text, preserve its substance and
add the disclosure at the beginning of the edited field.

Use `Assisted-by: <model or assistant> via <tool>` in commits when recording
assistance. Never list an AI system as a human author or co-author. Preserve
legitimate human authorship and contribution credits.

### Licensing and copyright

Contributors are responsible for ensuring that generated material can be
distributed under the [project license](../LICENSE). Check third-party licenses
and attribution before submitting code, text, or assets.

## Respect reviewer time

Submit work you can explain and evidence you have checked. Do not post
repetitive, unsolicited, or unreviewed generated comments. A contribution should
provide enough value to justify the effort needed to review and maintain it.
Maintainers may ask for revision or close work that shifts its basic
verification burden onto them.

## Prohibited uses

- Do not use AI to solve issues labeled “good first issue”; these are learning
  opportunities for new contributors.
- Do not submit unsolicited, repetitive, or low-quality generated comments or
  reviews.
- Do not accept or merge generated code without human review and verification.

This policy follows the contribution principles discussed by
[Astral](https://github.com/astral-sh/uv/blob/c89a78ec085077f6344b0439ddf07fdad7336310/CONTRIBUTING.md),
[Qiskit](https://github.com/Qiskit/qiskit/blob/cd8701690723d3d9602fac63fe0bd7ea618799be/CONTRIBUTING.md#use-of-ai-tools),
[LLVM](https://github.com/llvm/llvm-project/blob/9b6391f9c439c9926e8587b7b940e9a1e98a7819/llvm/docs/AIToolPolicy.md),
and the
[Fedora Council policy proposal](https://communityblog.fedoraproject.org/council-policy-proposal-policy-on-ai-assisted-contributions/)
(published under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)).
