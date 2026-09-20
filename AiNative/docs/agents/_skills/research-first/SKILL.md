---
name: research-first
description: Scans the codebase before planning or writing code. Use when starting a non-trivial feature, refactor, or any task that touches 2+ files or has ambiguous requirements.
---

# Research first

Do not write code or propose solutions until the codebase is understood.

## When to use

- Starting a non-trivial feature or refactor
- Task touches 2+ files or modules
- Requirements are ambiguous

## Behavior

1. Scan entry points and related files — reference exact paths, functions, line ranges
2. List modules affected, database impact, integration points, existing tests
3. Identify risk areas (auth, multi-tenancy, data integrity, breaking changes)
4. Flag open questions that block planning
5. Do not propose solutions or write code

## Output

Structured research report: files in scope, modules affected, database impact, patterns to follow, integration points, test coverage, risk areas, open questions.
