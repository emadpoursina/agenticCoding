"""Module entry point for the Hermes worker/CLI dispatcher."""

from .runtime import main

if __name__ == "__main__":
    raise SystemExit(main())

