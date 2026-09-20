---
name: mermaid-diagrams
description: Renders architecture, data-flow, and state diagrams in Mermaid with syntax constraints. Use when a plan or explanation needs a diagram of services, flows, or relationships.
---

# Mermaid diagrams

Use Mermaid when explaining architecture, data flows, or complex relationships.

## Syntax rules

- Do NOT use spaces in node IDs — use camelCase or underscores
- Do NOT use HTML tags or explicit colors
- Wrap labels with special characters in double quotes
- Use double quotes for edge labels with parentheses or commas
- Avoid reserved keywords as node IDs (`end`, `subgraph`, `graph`)
- For subgraphs, use `subgraph id [Label]` format
- Do not use `click` syntax

## When to use

- Architecture overviews in plans
- Data flow between services
- State machines or phase transitions
- Complex relationships that prose obscures
