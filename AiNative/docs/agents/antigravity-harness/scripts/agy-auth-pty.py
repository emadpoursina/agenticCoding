#!/usr/bin/env python3
"""Drive `agy` in a pty to complete Google OAuth sign-in without a browser.

The CLI's print mode (`agy -p`) gives the operator only 60 seconds to return an
authorization code, which is unusable when the browser is on another machine.
The interactive TUI waits indefinitely, so this script runs the TUI in a pty and
does only the mechanical parts:

  1. selects "Google OAuth" on the login-method menu,
  2. captures the authorization URL the CLI prints (it is word-wrapped there),
  3. waits for an authorization code to appear in a file,
  4. types that code into the CLI and submits it,
  5. exits once the token is stored.

The code travels through a file, not through a chat transcript.

Usage:
  agy-auth-pty.py --code-file /path/agy-auth-code.txt
                   [--url-file /path/agy-auth-url.txt]
                   [--log-file /path/agy-auth.log]
                   [--bin agy] [--run-seconds 1800]

Exit codes: 0 signed in (or already signed in), 2 driver gave up before a
sign-in completed, 3 the CLI exited early.
"""
import argparse
import fcntl
import os
import pty
import re
import select
import signal
import struct
import subprocess
import sys
import termios
import time

ANSI_RE = re.compile(rb"\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07\x1b]*(\x07|\x1b\\)|\x1b[()][A-Z0-9]|\x1b[=>]")
URL_HEAD = "https://accounts.google.com/o/oauth2/auth?"
URL_CHARS = re.compile(r"[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+")
MENU_MARK = b"Select login method"
CODE_PROMPT = b"authorization code"
SIGNED_IN_MARKS = (b"Authentication successful", b"Welcome to Antigravity CLI")


def strip_ansi(data: bytes) -> bytes:
    """Remove terminal escape sequences so text can be matched."""
    return ANSI_RE.sub(b"", data)


def extract_url(text: str) -> str:
    """Return the last complete authorization URL in the text.

    The TUI soft-wraps the URL and draws a box border after it, so take the last
    occurrence and cut at the first character that cannot belong to a URL.
    """
    i = text.rfind(URL_HEAD)
    if i < 0:
        return ""
    m = URL_CHARS.match(text[i:])
    url = m.group(0) if m else ""
    return url if ("&state=" in url and "code_challenge_method" in url) else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code-file", required=True, help="file the operator writes the authorization code into")
    ap.add_argument("--url-file", default="", help="where to write the captured authorization URL")
    ap.add_argument("--log-file", default="", help="where to write the raw pty transcript")
    ap.add_argument("--bin", default="agy", help="agy binary name or path")
    ap.add_argument("--run-seconds", type=int, default=1800, help="give up after this long")
    args = ap.parse_args()

    base_dir = os.path.dirname(os.path.abspath(args.code_file))
    url_file = args.url_file or os.path.join(base_dir, "agy-auth-url.txt")
    log_file = args.log_file or os.path.join(base_dir, "agy-auth.log")

    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 50, 1000, 0, 0))

    env = dict(os.environ)
    env.update({"TERM": "xterm-256color", "NO_COLOR": "1"})
    # Signal a remote session so the CLI prints a URL instead of trying to open a browser.
    env.setdefault("SSH_CONNECTION", "127.0.0.1 0 127.0.0.1 0")

    proc = subprocess.Popen([args.bin], stdin=slave, stdout=slave, stderr=slave,
                            start_new_session=True, env=env, close_fds=True)
    os.close(slave)
    os.set_blocking(master, False)

    log = open(log_file, "wb", buffering=0)
    buf = b""
    state = {"menu": False, "url": False, "code": False, "signed_in": False}

    def note(msg: str) -> None:
        log.write(("\n[driver] %s\n" % msg).encode())

    note("started pid=%d run_seconds=%d bin=%s" % (proc.pid, args.run_seconds, args.bin))
    t0 = time.time()
    rc = 2
    try:
        while time.time() - t0 < args.run_seconds:
            if proc.poll() is not None:
                note("agy exited rc=%s" % proc.returncode)
                rc = 0 if state["signed_in"] else 3
                break
            r, _, _ = select.select([master], [], [], 0.5)
            if r:
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    chunk = b""
                if chunk:
                    log.write(chunk)
                    buf = (buf + strip_ansi(chunk))[-16000:]
                    if not state["menu"] and MENU_MARK in buf:
                        note("login menu detected; selecting Google OAuth")
                        time.sleep(0.5)
                        os.write(master, b"\r")
                        state["menu"] = True
                    if not state["url"]:
                        url = extract_url(buf.decode("utf-8", "replace"))
                        if url:
                            with open(url_file, "w") as fh:
                                fh.write(url + "\n")
                            note("URL captured (%d chars) -> %s" % (len(url), url_file))
                            state["url"] = True
                    if any(m in buf for m in SIGNED_IN_MARKS):
                        state["signed_in"] = True
            if state["menu"] and not state["code"] and CODE_PROMPT in buf and os.path.exists(args.code_file):
                try:
                    code = open(args.code_file).read().strip()
                except OSError:
                    code = ""
                if code:
                    note("code received (%d chars); submitting" % len(code))
                    os.write(master, code.encode() + b"\r")
                    state["code"] = True
                    try:
                        os.remove(args.code_file)
                    except OSError:
                        pass
            if state["code"] and state["signed_in"]:
                note("sign-in confirmed; waiting for token to be stored")
                time.sleep(5)
                rc = 0
                break
        if not state["menu"] and not state["code"]:
            note("no login menu appeared; the CLI is already signed in")
            rc = 0
        elif state["menu"] and not state["url"]:
            note("login menu shown but no authorization URL captured")
            rc = 2
    finally:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            pass
        time.sleep(1)
        try:
            proc.kill()
        except Exception:
            pass
        note("driver finished state=%s rc=%d" % (state, rc))
        log.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())
