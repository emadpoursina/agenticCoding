# Headless sign-in for the Antigravity CLI

Provisions `agy` on a machine that has **no browser** (container, CI, remote
shell) and no keyring, so the harness can dispatch jobs. This is a one-time
operator step taken on request — it is **not** part of the dispatch path.
During a job, `rule.md` still governs: if `agy` is missing or `agy models` fails,
stop.

Verified against `agy` 1.5.5 on `linux/arm64` (Debian 13, no Secret Service,
no `gcloud`).

## 1. Install the CLI

```bash
curl -fsSL https://antigravity.google/cli/install.sh | bash
```

The official installer downloads a flat native build from Google's release
server, verifies its SHA-512 against the platform manifest, and installs to
`~/.local/bin/agy`. It also appends that directory to `~/.profile` and
`~/.zshrc`. Confirm:

```bash
agy --version      # 1.5.5
```

`agy update` self-updates; version numbers here are evidence, not requirements.

## 2. Pick an authentication mode

| Mode | When | How |
| --- | --- | --- |
| Local keyring | Desktop machine, CLI signed in already | Automatic; no prompt |
| Browser OAuth | **No browser, operator has one elsewhere** | Section 3 below |
| Gemini API key | Headless/CI, no account session wanted | `"modelProvider": "gemini"` in `~/.gemini/antigravity-cli/settings.json` plus `GEMINI_API_KEY` in the environment |
| ADC | Google Cloud identity already configured | `gcloud auth application-default login` |

A bare `GEMINI_API_KEY` alone does nothing — the `modelProvider` setting is what
selects that path. It runs anonymous to your account, so prefer OAuth when the
account is the one that should be billed.

## 3. Browser OAuth from a machine with no browser

`agy -p` prints a URL and then allows exactly **60 seconds** for the
authorization code (`Waiting for authentication (timeout 60s)...`). A
`loginTimeout` key in `settings.json` did not change that on 1.5.5, so print
mode cannot be used — a human on another machine needs minutes. The interactive
TUI waits indefinitely, so run the TUI in a pty instead.

1. Start the driver in the background:

   ```bash
   python3 scripts/agy-auth-pty.py --code-file /tmp/agy-auth-code.txt
   ```

   It selects "Google OAuth" on the login menu itself and writes the URL to
   `/tmp/agy-auth-url.txt` (next to the code file by default; override with
   `--url-file`). The URL is bound to that live process — restart the driver if
   it expires or if the process dies.

2. Give the URL to the operator. They open it in their own browser, sign in
   with the account that holds the Antigravity access, approve the consent
   screen, and land on `antigravity.google/oauth-callback`, which displays a
   long authorization code.

3. The operator writes that code — alone, on one line — into the `--code-file`.
   A file is used on purpose: an authorization code is a live credential and
   must not travel through a chat transcript.

4. The driver submits it, sees the CLI reach `Authentication successful` /
   `Welcome to Antigravity CLI`, waits for the token to be written, and exits 0.

5. Delete the code file, the URL file, and the log. The log contains the code
   the driver typed.

Result: `~/.gemini/antigravity-cli/antigravity-oauth-token` (mode 600). No
keyring is required; the CLI falls back to that file. It refreshes on its own.

## 4. Verify

```bash
agy models                                  # lists IDs; "Please sign in" means not authenticated
agy -p "Reply with exactly: HARNESS OK"     # must print HARNESS OK, exit 0
```

Then prove the harness path end to end:

```bash
python3 agy-spawn.py --name verify --cwd "$PWD" \
  --model gemini-3.8-flash-high --scout --timeout 240 \
  -- "Goal: confirm the harness works. Report: STATUS: ok | STATUS: stuck, SUMMARY, files changed."
```

Read `report.json` and require `lifecycle=completed`, `reportValid=true`,
`workerStatus=ok`. A `completed` lifecycle alone only means the process exited 0.

`agy models` is the authority for `--model` values; Flash variants carry
`-high` / `-medium` / `-low` suffixes (`gemini-3.8-flash-high`).

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `agy not on PATH` from `agy-spawn.py`, exit 127 | CLI not installed, or `~/.local/bin` missing from PATH | Re-run the installer; confirm `which agy` |
| `Please sign in to view available models` | Installed, not authenticated | Section 3 |
| Print mode says `authentication failed or timed out` after 60 s | Print-mode login window is too short for a remote human | Use the pty driver, do not raise `--timeout` |
| Captured URL ends mid-scope or has box-drawing characters | The TUI soft-wraps the URL and draws a border after it | Take the last occurrence and cut at the first non-URL character; the driver does this |
| `pkill -f agy` kills the operator's own shell | The pattern matches the invoking command line too | Track the driver pid, or match a distinctive pattern like `agy_auth` |
| First interactive run shows a theme picker | TUI onboarding, not an auth failure | Print mode bypasses it; finish onboarding later if you use the TUI |
| Token file gone after a restart | Container home not persisted | Keep `~/.gemini/antigravity-cli/` on a volume |
