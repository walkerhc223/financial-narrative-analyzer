---
name: fna-conventions
description: Architecture and conventions for the Financial Narrative Analyzer (FNA) project. Use when writing, reviewing, or extending code in this repo — especially anything touching computation.py, the YAML semantic registry, materiality logic, or the decision/interpretation layer.
---

# FNA Project Conventions

## Core architectural principle: deterministic computation first

FNA separates **computation** from **interpretation** from **narrative generation**. These are three distinct layers and must stay distinct:

1. **Computation layer** (`computation.py` and similar) — pure, deterministic Python. Takes structured financial data in, produces structured numeric results out. No LLM calls. No narrative text. Every function here should be independently unit-testable with known inputs and expected outputs.
2. **Decision/interpretation layer** — applies materiality thresholds and the YAML semantic registry to decide *which* computed facts are worth surfacing and *how* they should be classified. This layer decides significance, not wording.
3. **Narrative layer** — LLM-driven. Takes the already-decided, already-classified facts from layer 2 and turns them into prose. The LLM should never be asked to also do the arithmetic or the materiality judgment — those must already be settled by the time a prompt is constructed.

When writing or reviewing code, flag any instance where a later layer is doing a job that belongs to an earlier one — e.g., an LLM prompt containing raw computation, or a narrative function silently applying its own threshold logic.

## Materiality threshold

Default materiality threshold is **1% of revenue**. Any variance or line-item change below this threshold is treated as immaterial by default and should not be surfaced as a narrative-worthy finding unless explicitly flagged otherwise (e.g., a small-dollar item that's qualitatively significant, like a new related-party transaction). Threshold logic should live in the decision layer, not be hardcoded inline in narrative prompts or computation functions.

## YAML semantic registry

Financial line items, categories, and their relationships are defined centrally in a YAML semantic registry rather than scattered as string literals across the codebase. When adding support for a new line item or category:
- Add it to the registry first.
- Reference it by its registry key everywhere else in the code.
- Don't introduce a new ad hoc string identifier for something the registry already models.

## Testing expectations

- Computation-layer functions require unit tests with explicit input/output pairs — this is non-negotiable given the deterministic-first design. A computation change without a corresponding test update is incomplete.
- When reviewing a PR or diff, check whether test coverage in `computation.py` (or wherever computation logic lives) was updated alongside the logic change.
- Prefer small, composable, pure functions in the computation layer — they're easier to test in isolation and easier for an LLM-assisted reviewer to verify by inspection.

## When reviewing or extending code

- Ask: which layer does this belong to? If a change mixes layers (e.g., a computation function that also decides materiality, or a narrative prompt that also computes a variance), suggest splitting it.
- Prefer explicit, named thresholds and registry lookups over magic numbers or inline strings.
- Keep the registry and the threshold logic as the single sources of truth — don't let convenience duplicate them elsewhere.
