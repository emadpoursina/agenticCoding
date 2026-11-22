# Client proposal HTML

Every client proposal is a **single self-contained HTML file**. No Markdown
as the client deliverable. No separate CSS/JS files. No CDN fonts required
(system stack is enough; optional `fonts.googleapis.com` for Vazirmatn on
Persian only).

## Document

```html
<!DOCTYPE html>
<html lang="en">
<!-- lang="fa" dir="rtl" when Persian -->
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title><!-- product or client name — Proposal --></title>
  <style>/* all CSS here */</style>
</head>
<body>
  <!-- visual document -->
</body>
</html>
```

Default path: `PROPOSAL.html` at the project root (or the path the user
names). If that file exists, ask overwrite, merge, or another name.

## Visual system

Pick **one** palette and use it throughout. Defaults:

| Token | Light professional (EN default) |
|-------|----------------------------------|
| `--bg` | `#f4f1ea` warm paper |
| `--surface` | `#ffffff` |
| `--ink` | `#1c1917` |
| `--muted` | `#57534e` |
| `--accent` | `#0f766e` teal |
| `--accent-2` | `#c2410c` terracotta, sparingly |
| `--line` | `#e7e5e4` |

Persian: same tokens; load Vazirmatn; `dir="rtl"`; **never** `letter-spacing`
on Persian text.

Effects (use all of these, keep them quiet):

- Full-page paper background plus a thin **accent gradient bar** at the top
  (`linear-gradient` along the reading start edge).
- **Hero** block: product name, one-line outcome, optional client name. Soft
  shadow, large type, accent underline or pill for the document type
  (Proposal / پیشنهاد همکاری).
- **Cards** for phases, deliverables, and investment: white surface, 1px
  line, 12–16px radius, hover lift (`translateY(-2px)` + shadow). No bounce.
- **Timeline** as a vertical accent rail with numbered nodes — not a
  mermaid diagram and not an architecture drawing.
- **Investment** callout: accent-tinted panel, large approved figure, payment
  schedule as a compact table.
- Section labels in small caps / tracking **only on Latin**. Fade-in on
  first paint (`@keyframes` opacity, 400ms, `prefers-reduced-motion: reduce`
  disables it).
- Print: `@media print` — white background, no hover, no animation, cards
  unboxed enough to read on paper.

Do not: stock Unsplash heroes, emoji headers, neon, glassmorphism, AI-slop
purple gradients, decorative charts with fake numbers, architecture
diagrams, or schemas.

## Sections as layout

Map the proposal sections to visual blocks. Omit a block if it has nothing
true to say.

1. Hero — Project Overview
2. Proposed Solution — short prose + 3–5 outcome chips (qualitative unless
   the PRD has numbers)
3. Scope — two columns when useful: in scope / out of scope
4. Phases — card grid or timeline; table is fine inside a card
5. Timeline — duration and milestones; never invent dates
6. Investment — approved price only; recurring costs in a second row
7. Assumptions — muted secondary card
8. Next steps — numbered, accent numbers

Length still 1–3 screens. Color is structure, not decoration for its own
sake.

## Public URL (when the project has a backend)

After the HTML file is written, look for an **existing HTTP backend** in
this repo (Express/Fastify/Koa, FastAPI/Flask/Django, Next.js/Nuxt, Rails,
Go `net/http`, etc.).

**If a backend exists:**

- Serve `PROPOSAL.html` as **GET**, **no auth**, so the client can open a
  link.
- Prefer the stack's existing static/public folder when that folder is
  already public (`public/proposal.html`, `static/proposal.html`, Next
  `public/proposal.html` → `/proposal.html`).
- Otherwise add the smallest route the framework already uses, e.g.
  `GET /proposal` returning the file as `text/html; charset=utf-8`.
- Do not put the file behind the app's login, CSRF, or API key middleware.
- Do not scaffold a new server, add a framework, or deploy anything.
- Do not commit secrets into the HTML.

**If there is no backend:** leave `PROPOSAL.html` in the repo. Do not invent
a host. Report `URL: none`.

The public path is for easy client access. Treat the document as
share-by-link; if the developer asks for a private link, stop and ask how
they want it gated — do not invent auth.

Report the path the deployed app would expose (`/proposal` or
`/proposal.html`), not a guessed production domain unless the project
already documents one.
