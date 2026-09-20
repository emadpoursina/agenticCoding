#!/usr/bin/env node
// Validate relative links in markdown docs. Resolves links relative to the
// containing file; also accepts repo-root-relative paths (e.g. `docs/agents/x`
// used inside `.cursor/rules/*.mdc`). Exits non-zero on any broken link.
//
//   node scripts/check-doc-links.mjs [root]

import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.argv[2] ?? path.join(import.meta.dirname, ".."));

function walk(dir, out = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === ".git" || entry.name === "node_modules") continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, out);
    else if (/\.(md|mdc)$/.test(entry.name)) out.push(full);
  }
  return out;
}

const broken = [];
for (const file of walk(root)) {
  const text = fs.readFileSync(file, "utf8");
  const re = /\]\(([^)\s]+)\)/g;
  let match;
  while ((match = re.exec(text))) {
    let link = match[1];
    if (/^(https?:|mailto:|#)/.test(link)) continue;
    const hash = link.indexOf("#");
    if (hash >= 0) link = link.slice(0, hash);
    if (!link) continue;
    const candidates = link.startsWith("/")
      ? [path.join(root, link)]
      : [path.resolve(path.dirname(file), link), path.join(root, link)];
    if (!candidates.some((c) => fs.existsSync(c))) {
      broken.push(`${path.relative(root, file)}  ->  ${match[1]}`);
    }
  }
}

if (broken.length > 0) {
  console.error(`BROKEN LINKS (${broken.length}):`);
  for (const line of [...new Set(broken)].sort()) console.error(`  ${line}`);
  process.exit(1);
}
console.log(`OK: all relative links resolve (${walk(root).length} files scanned)`);
