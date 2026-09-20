#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import {
  copyFileSync,
  existsSync,
  lstatSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  readlinkSync,
  rmSync,
  symlinkSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const AGENT_ALERT_HOOK = "./hooks/agent-alert.sh";
const GLOBAL_HOOK_ENTRIES = {
  stop: [{ command: `${AGENT_ALERT_HOOK} stop`, timeout: 5 }],
  preToolUse: [
    {
      command: `${AGENT_ALERT_HOOK} ask`,
      matcher: "^(AskQuestion|SwitchMode)$",
      timeout: 5,
    },
  ],
};

const GITIGNORE_MARKER = "# Personal AiNative symlinks (machine-local)";
const GITIGNORE_BLOCK = `
${GITIGNORE_MARKER}
.cursor/rules/personal
docs/agents
docs/systems
`;

// Old numbered-layout symlink entries → new layout (ADR-003).
const SYMLINK_GITIGNORE_MIGRATIONS = [
  ["docs/8-agents", "docs/agents"],
  ["docs/2-ai-workflows", "docs/systems"],
];

function escapeRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function linePresent(text, line) {
  return new RegExp(`^${escapeRegex(line)}\\s*$`, "m").test(text);
}

// Replace stale numbered symlink entries with the new ones and make sure both
// new entries are ignored, even when the marker block already exists.
function migrateSymlinkGitignore(text) {
  let updated = text;

  for (const [oldLine, newLine] of SYMLINK_GITIGNORE_MIGRATIONS) {
    if (!linePresent(updated, oldLine)) continue;
    if (linePresent(updated, newLine)) {
      updated = updated.replace(new RegExp(`^${escapeRegex(oldLine)}\\s*\\n?`, "m"), "");
    } else {
      updated = updated.replace(new RegExp(`^${escapeRegex(oldLine)}\\s*$`, "m"), newLine);
    }
  }

  if (updated.includes(GITIGNORE_MARKER)) {
    for (const [, newLine] of SYMLINK_GITIGNORE_MIGRATIONS) {
      if (!linePresent(updated, newLine)) {
        const separator = updated.endsWith("\n") ? "" : "\n";
        updated = `${updated}${separator}${newLine}\n`;
      }
    }
  }

  return updated;
}

const SCRATCH_GITIGNORE_MARKER = "# Scratch — agent-accessible temp files (not committed)";
const SCRATCH_GITIGNORE_BLOCK = `
${SCRATCH_GITIGNORE_MARKER}
scratch/*
!scratch/README.md
`;

const scriptDir = path.dirname(fileURLToPath(import.meta.url));

function usage() {
  console.log(`Usage:
  setup-machine.sh [--ainative-home <path>]
  setup-project.sh [DIR] [--ainative-home <path>] [--force-workflows]
  ainative-link.mjs status [DIR] [--ainative-home <path>]

  (wrappers: scripts/setup-machine.sh, scripts/setup-project.sh)
  Direct:    node scripts/ainative-link.mjs <machine|project|status> ...

Home: this checkout (scripts/..). Fallback: $AINATIVE_HOME if that tree is valid.
Override: --ainative-home <path> (errors if that path is not a valid checkout).

machine  — install/repair global Cursor slash commands + alert hook (~/.cursor)
project  — install/repair AiNative agents/rules in one repo (new or existing)
status   — report machine + project symlink health`);
}

function parseArgs(argv) {
  const positional = [];
  let ainativeHome = "";
  let forceWorkflows = false;

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--ainative-home") {
      ainativeHome = argv[i + 1] ?? "";
      i += 1;
      continue;
    }
    if (arg === "--force-workflows") {
      forceWorkflows = true;
      continue;
    }
    if (arg === "--help" || arg === "-h") {
      usage();
      process.exit(0);
    }
    positional.push(arg);
  }

  return { positional, ainativeHome, forceWorkflows };
}

function isHealthyAinativeHome(dir) {
  if (!dir) {
    return false;
  }
  const resolved = path.resolve(dir);
  return (
    existsSync(path.join(resolved, "docs/agents")) &&
    existsSync(path.join(resolved, ".cursor/commands"))
  );
}

function failInvalidHome(label, dir) {
  console.error(`error: ${label} is not a valid AiNative checkout: ${dir}`);
  console.error("expected docs/agents and .cursor/commands");
  process.exit(1);
}

function resolveAinativeHome(flagHome) {
  if (flagHome) {
    if (!isHealthyAinativeHome(flagHome)) {
      failInvalidHome("--ainative-home", flagHome);
    }
    return path.resolve(flagHome);
  }

  const inferred = path.resolve(scriptDir, "..");
  if (isHealthyAinativeHome(inferred)) {
    return inferred;
  }

  const fromEnv = process.env.AINATIVE_HOME ?? "";
  if (isHealthyAinativeHome(fromEnv)) {
    return path.resolve(fromEnv);
  }

  if (fromEnv) {
    failInvalidHome("AINATIVE_HOME", fromEnv);
  }
  failInvalidHome("this checkout", inferred);
}

function assertNotAinativeHome(projectRoot, ainativeHome) {
  if (path.resolve(projectRoot) === path.resolve(ainativeHome)) {
    console.error(
      "error: refusing to link a project into AiNative itself — run setup-project.sh from an app repo",
    );
    process.exit(1);
  }
}

function ensureDir(dir) {
  mkdirSync(dir, { recursive: true });
}

function forceSymlink(target, linkPath) {
  const absoluteTarget = path.resolve(target);
  try {
    const stat = lstatSync(linkPath);
    if (stat.isSymbolicLink()) {
      // Node rmSync does not remove broken symlinks on macOS; unlink does.
      unlinkSync(linkPath);
    } else if (stat.isFile() || stat.isDirectory()) {
      rmSync(linkPath, { recursive: true, force: true });
    }
  } catch (err) {
    if (err && typeof err === "object" && "code" in err && err.code !== "ENOENT") {
      throw err;
    }
  }
  symlinkSync(absoluteTarget, linkPath);
}

function readGitCommit(ainativeHome) {
  try {
    return execFileSync("git", ["log", "-1", "--format=%h %s"], {
      cwd: ainativeHome,
      encoding: "utf8",
    }).trim();
  } catch {
    return "unknown";
  }
}

function hookUsesAgentAlert(entry) {
  return typeof entry?.command === "string" && entry.command.includes("agent-alert.sh");
}

function mergeGlobalHooks(existingHooks) {
  const merged = { ...(existingHooks ?? {}) };

  for (const [event, entries] of Object.entries(GLOBAL_HOOK_ENTRIES)) {
    const current = Array.isArray(merged[event]) ? [...merged[event]] : [];
    if (!current.some(hookUsesAgentAlert)) {
      current.push(...entries);
    }
    merged[event] = current;
  }

  return merged;
}

function linkMachineHooks(ainativeHome) {
  const scriptSource = path.join(ainativeHome, ".cursor", "hooks", "agent-alert.sh");
  const hooksDir = path.join(homedir(), ".cursor", "hooks");
  const hooksJsonPath = path.join(homedir(), ".cursor", "hooks.json");

  if (!existsSync(scriptSource)) {
    console.error(`error: hook script not found: ${scriptSource}`);
    process.exit(1);
  }

  ensureDir(hooksDir);
  forceSymlink(scriptSource, path.join(hooksDir, "agent-alert.sh"));

  let hooksConfig = { version: 1, hooks: {} };
  if (existsSync(hooksJsonPath)) {
    try {
      hooksConfig = JSON.parse(readFileSync(hooksJsonPath, "utf8"));
    } catch (err) {
      console.error(`error: could not parse ${hooksJsonPath}`);
      throw err;
    }
  }

  hooksConfig.version = hooksConfig.version ?? 1;
  hooksConfig.hooks = mergeGlobalHooks(hooksConfig.hooks);
  writeFileSync(hooksJsonPath, `${JSON.stringify(hooksConfig, null, 2)}\n`, "utf8");

  console.log(`Linked agent alert hook → ${hooksDir}`);
  console.log(`Updated global hooks → ${hooksJsonPath}`);
}

function countGlobalCommands() {
  const globalCommandsDir = path.join(homedir(), ".cursor", "commands");
  if (!existsSync(globalCommandsDir)) {
    return 0;
  }
  return readdirSync(globalCommandsDir).filter((name) => {
    const fullPath = path.join(globalCommandsDir, name);
    try {
      return name.endsWith(".md") && lstatSync(fullPath).isSymbolicLink();
    } catch {
      return false;
    }
  }).length;
}

function ensureGitignore(projectRoot) {
  const gitignorePath = path.join(projectRoot, ".gitignore");
  const existing = existsSync(gitignorePath) ? readFileSync(gitignorePath, "utf8") : "";
  let updated = existing;
  let changed = false;

  const migrated = migrateSymlinkGitignore(updated);
  if (migrated !== updated) {
    updated = migrated;
    changed = true;
  }

  if (!updated.includes(GITIGNORE_MARKER)) {
    const separator = updated.length > 0 && !updated.endsWith("\n") ? "\n" : "";
    updated = `${updated}${separator}${GITIGNORE_BLOCK.trimStart()}\n`;
    changed = true;
  }

  if (!updated.includes(SCRATCH_GITIGNORE_MARKER) && !/\bscratch\/\s*$/.test(updated)) {
    const separator = updated.length > 0 && !updated.endsWith("\n") ? "\n" : "";
    updated = `${updated}${separator}${SCRATCH_GITIGNORE_BLOCK.trimStart()}\n`;
    changed = true;
  }

  if (changed) {
    writeFileSync(gitignorePath, updated, "utf8");
  }

  return changed;
}

function ensureScratchFolder(projectRoot, ainativeHome) {
  const scratchDir = path.join(projectRoot, "scratch");
  const readmePath = path.join(scratchDir, "README.md");
  const readmeSource = path.join(ainativeHome, "scratch", "README.md");

  ensureDir(scratchDir);

  if (existsSync(readmePath)) {
    return false;
  }

  if (!existsSync(readmeSource)) {
    console.warn(`warn: scratch README not found at ${readmeSource}`);
    return false;
  }

  copyFileSync(readmeSource, readmePath);
  return true;
}

function isGitRepo(projectRoot) {
  return existsSync(path.join(projectRoot, ".git"));
}

function showStatus(projectRoot, ainativeHome) {
  const commit = readGitCommit(ainativeHome);
  console.log(`AiNative: ${commit}`);

  const rulesLink = path.join(projectRoot, ".cursor", "rules", "personal");
  const agentsLink = path.join(projectRoot, "docs", "agents");

  if (existsSync(rulesLink) && lstatSync(rulesLink).isSymbolicLink()) {
    console.log(`  rules:    .cursor/rules/personal → ${readlinkSync(rulesLink)}`);
  } else if (isGitRepo(projectRoot)) {
    console.log("  rules:    missing — run: ./scripts/setup-project.sh <app>");
  }

  if (existsSync(agentsLink) && lstatSync(agentsLink).isSymbolicLink()) {
    console.log(`  agents:   docs/agents → ${readlinkSync(agentsLink)}`);
  } else if (isGitRepo(projectRoot)) {
    console.log("  agents:   missing — run: ./scripts/setup-project.sh <app>");
  }

  const scratchReadme = path.join(projectRoot, "scratch", "README.md");
  if (existsSync(scratchReadme)) {
    console.log("  scratch:  scratch/README.md");
  } else if (isGitRepo(projectRoot)) {
    console.log("  scratch:  missing — run: ./scripts/setup-project.sh <app>");
  }

  const hooksJsonPath = path.join(homedir(), ".cursor", "hooks.json");
  const hookScriptPath = path.join(homedir(), ".cursor", "hooks", "agent-alert.sh");

  console.log(`  commands: ${countGlobalCommands()} global (in ~/.cursor/commands/)`);

  if (existsSync(hookScriptPath) && lstatSync(hookScriptPath).isSymbolicLink()) {
    console.log(`  hooks:    ~/.cursor/hooks/agent-alert.sh → ${readlinkSync(hookScriptPath)}`);
  } else if (existsSync(hookScriptPath)) {
    console.log(`  hooks:    ~/.cursor/hooks/agent-alert.sh (present)`);
  } else {
    console.log("  hooks:    missing — run: ./scripts/setup-machine.sh");
  }

  if (existsSync(hooksJsonPath)) {
    try {
      const hooksConfig = JSON.parse(readFileSync(hooksJsonPath, "utf8"));
      const events = Object.entries(hooksConfig.hooks ?? {}).filter(([, entries]) =>
        Array.isArray(entries) && entries.some(hookUsesAgentAlert),
      );
      if (events.length > 0) {
        console.log(`  alerts:   ${events.map(([name]) => name).join(", ")}`);
      }
    } catch {
      console.log("  alerts:   ~/.cursor/hooks.json present (could not parse)");
    }
  }
}

function linkMachine(ainativeHome) {
  const commandsSource = path.join(ainativeHome, ".cursor", "commands");
  const commandsTarget = path.join(homedir(), ".cursor", "commands");

  if (!existsSync(commandsSource)) {
    console.error(`error: commands directory not found: ${commandsSource}`);
    process.exit(1);
  }

  ensureDir(commandsTarget);

  const files = readdirSync(commandsSource).filter((name) => name.endsWith(".md"));
  for (const name of files) {
    forceSymlink(path.join(commandsSource, name), path.join(commandsTarget, name));
  }

  console.log(`Linked ${files.length} global commands → ${commandsTarget}`);
  linkMachineHooks(ainativeHome);
  console.log("Restart Cursor, then run setup-project.sh in each app repo.");
}

function removeStaleSymlink(linkPath, label) {
  try {
    if (lstatSync(linkPath).isSymbolicLink()) {
      unlinkSync(linkPath);
      console.log(`Removed stale symlink ${label}`);
    }
  } catch (err) {
    if (err && typeof err === "object" && "code" in err && err.code !== "ENOENT") {
      throw err;
    }
  }
}

function linkProject(projectRoot, ainativeHome, forceWorkflows) {
  const resolvedRoot = path.resolve(projectRoot);
  assertNotAinativeHome(resolvedRoot, ainativeHome);
  ensureDir(path.join(resolvedRoot, ".cursor", "rules"));
  ensureDir(path.join(resolvedRoot, "docs"));

  // Clean break from the old numbered layout (docs/8-agents, docs/2-ai-workflows).
  removeStaleSymlink(path.join(resolvedRoot, "docs", "8-agents"), "docs/8-agents");
  removeStaleSymlink(path.join(resolvedRoot, "docs", "2-ai-workflows"), "docs/2-ai-workflows");

  const aiRulesTarget = path.join(resolvedRoot, ".cursor", "rules", "ai-rules.mdc");
  const aiRulesTemplate = path.join(
    ainativeHome,
    "docs/systems/ai-rules-template.md",
  );

  if (!existsSync(aiRulesTarget)) {
    if (!existsSync(aiRulesTemplate)) {
      console.error(`error: template not found: ${aiRulesTemplate}`);
      process.exit(1);
    }
    copyFileSync(aiRulesTemplate, aiRulesTarget);
    console.log("Created .cursor/rules/ai-rules.mdc (edit for this project)");
  } else {
    console.log("Kept existing .cursor/rules/ai-rules.mdc");
  }

  forceSymlink(
    path.join(ainativeHome, ".cursor", "rules"),
    path.join(resolvedRoot, ".cursor", "rules", "personal"),
  );
  forceSymlink(
    path.join(ainativeHome, "docs", "agents"),
    path.join(resolvedRoot, "docs", "agents"),
  );

  const workflowsLink = path.join(resolvedRoot, "docs", "systems");
  const workflowsSource = path.join(ainativeHome, "docs", "systems");

  if (existsSync(workflowsLink) && !lstatSync(workflowsLink).isSymbolicLink()) {
    if (forceWorkflows) {
      rmSync(workflowsLink, { recursive: true, force: true });
      forceSymlink(workflowsSource, workflowsLink);
      console.log("Replaced docs/systems with symlink (--force-workflows)");
    } else {
      console.warn(
        "warn: docs/systems exists as a real folder — skipped (use --force-workflows to replace)",
      );
    }
  } else {
    forceSymlink(workflowsSource, workflowsLink);
  }

  if (ensureScratchFolder(resolvedRoot, ainativeHome)) {
    console.log("Created scratch/README.md");
  }

  if (ensureGitignore(resolvedRoot)) {
    console.log("Updated .gitignore");
  }

  showStatus(resolvedRoot, ainativeHome);
}

function main() {
  const { positional, ainativeHome: explicitHome, forceWorkflows } = parseArgs(
    process.argv.slice(2),
  );
  const command = positional[0];

  if (!command) {
    usage();
    process.exit(1);
  }

  const ainativeHome = resolveAinativeHome(explicitHome);
  const targetDir = positional[1] ? path.resolve(positional[1]) : process.cwd();

  switch (command) {
    case "machine":
      linkMachine(ainativeHome);
      break;
    case "project":
      linkProject(targetDir, ainativeHome, forceWorkflows);
      break;
    case "status":
      showStatus(targetDir, ainativeHome);
      break;
    default:
      usage();
      process.exit(1);
  }
}

main();
