# Infrastructure patterns

Opinionated infra notes — updated in place as views evolve.

## Local shared services (Docker)

One compose stack on the dev machine hosts databases used by every project. Projects connect to `localhost` ports instead of running their own DB containers.

- **Canonical compose:** `/Users/emad/docker-infrastructure/docker-compose.yml`
- **Docs:** [local-shared-services.md](../setup/local-shared-services.md)
- **Per-project:** create databases/schemas inside the shared instances; keep app-specific compose for the app only

Trade-off: simpler resource use and one place to upgrade images; all projects share the same DB process (fine for local dev, not for isolation testing).
