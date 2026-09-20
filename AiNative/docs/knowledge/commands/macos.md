# macOS commands

## Clipboard

### cb2f — copy image file to clipboard

Add to `~/.zshrc`:

```bash
cb2f() {
  local f="${1:?usage: cb2f <image-file>}"
  [[ -f "$f" ]] || { echo "cb2f: not a file: $f" >&2; return 1; }

  case "${f:l}" in
    *.png)        osascript -e "set the clipboard to (read (POSIX file \"$f\") as «class PNGf»)" ;;
    *.jpg|*.jpeg) osascript -e "set the clipboard to (read (POSIX file \"$f\") as JPEG picture)" ;;
    *.gif)        osascript -e "set the clipboard to (read (POSIX file \"$f\") as «class GIFf»)" ;;
    *.tif|*.tiff) osascript -e "set the clipboard to (read (POSIX file \"$f\") as TIFF picture)" ;;
    *)            echo "cb2f: unsupported type (use png, jpg, gif, or tiff)" >&2; return 1 ;;
  esac
}
```

Reload: `source ~/.zshrc`

```bash
cb2f screenshot.png
# Paste with Cmd+V in an image-aware app (Preview, Slack, etc.)
```

Verify clipboard type:

```bash
osascript -e 'clipboard info'
```
