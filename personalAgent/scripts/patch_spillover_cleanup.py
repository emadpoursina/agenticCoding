from pathlib import Path

p = Path("/opt/hermes/tools/tool_result_storage.py")
text = p.read_text(encoding="utf-8")
if "def cleanup_spillover_cache(" in text:
    print("already present")
    raise SystemExit(0)
text += """

def cleanup_spillover_cache(max_age_hours: int = 24) -> int:
    import os
    import time
    from pathlib import Path as _P

    home = os.environ.get("HERMES_HOME") or str(_P.home() / ".hermes")
    d = _P(home) / "cache" / "spillover"
    if not d.is_dir():
        return 0
    cutoff = time.time() - max_age_hours * 3600
    removed = 0
    for f in d.iterdir():
        try:
            if f.is_file() and f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        except OSError:
            continue
    return removed
"""
p.write_text(text, encoding="utf-8")
print("patched", p)
