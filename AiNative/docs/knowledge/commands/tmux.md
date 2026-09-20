# Tmux

```bash
tmux ls
tmux att -t [sessionName]
tmux new -s [my_session_name]
```

## Ctrl+b

- List sessions: `w`
- New window: `c`
- Kill current pane: `x`

## Ctrl+b :

- `rename-session [name]`
- `rename-window [name]`
- `setw synchronize-panes [on/off]`
- `attach-session -t . -c /path/to/directory` — change the session base directory (new panes use this cwd)
