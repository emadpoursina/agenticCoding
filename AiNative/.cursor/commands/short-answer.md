# Short Answer Command

This file defines the short-answer command, which answers a question with minimal prose.

## Command Definition

```yaml
name: short-answer
description: Answer in a short, direct response — no lengthy explanations
```

## Invocation

When this command is invoked, the agent should:

1. **Parse Arguments**
   - `$ARGUMENTS` is the user's question or task
   - If empty, ask what they want answered

2. **Respond Concisely**
   - Lead with the direct answer in 1–3 sentences
   - Skip preamble, recap, and filler
   - Use bullets only when they clarify (max 5 short items)
   - Omit "let me know if…" and other engagement bait unless blocked
   - Show code only when needed; keep snippets minimal
   - Do not explain obvious steps or restate the question

3. **When Unsure**
   - Ask one short clarifying question instead of guessing at length

## Usage Examples

```text
/short-answer what's the difference between merge and rebase?
```

→ One-paragraph answer, no tutorial

```text
/short-answer is this repo using pnpm or bun?
```

→ Direct answer, maybe one supporting detail
