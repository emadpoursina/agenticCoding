from pathlib import Path

p = Path("/opt/hermes/hermes_cli/models.py")
text = p.read_text(encoding="utf-8")
needle = "def normalize_opencode_model_id("
if "def opencode_provider_family(" in text:
    print("already present")
    raise SystemExit(0)
if needle not in text:
    raise SystemExit("needle missing")
fn = '''
def opencode_provider_family(provider_id: Optional[str]) -> Optional[str]:
    """Resolve a provider id to its OpenCode family, or None.

    Returns ``"opencode-zen"`` or ``"opencode-go"`` for the built-in
    providers AND for custom providers whose name extends a family slug.
    Matching is case-insensitive.
    """
    raw = str(provider_id or "").strip().lower()
    if not raw:
        return None
    canonical = normalize_provider(provider_id)
    if canonical in {"opencode-zen", "opencode-go", "opencode-free"}:
        return canonical
    if raw.startswith("opencode-free"):
        return "opencode-free"
    if raw.startswith("opencode-go"):
        return "opencode-go"
    if raw.startswith("opencode-zen"):
        return "opencode-zen"
    return None


'''
p.write_text(text.replace(needle, fn + needle, 1), encoding="utf-8")
print("patched", p)
