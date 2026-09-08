# Minecraft Builder Headless Environment

This repository contains the reproducible configuration, source code, operating
documentation, and curated acceptance evidence for the Ubuntu Minecraft server,
HeadlessMC render worker, Visual Probe, and active environment projects.

It intentionally does not contain Minecraft worlds, server/client runtime
caches, downloaded mod binaries, authentication material, or raw run output.

## Layout

- `config/`: sanitized version-controlled service configuration.
- `scripts/`: operator entry points such as `connect.bash`.
- `docs/`: current operational and architecture documentation.
- `mc-visual-probe/`: Fabric client-mod source.
- `src/` and `tools/`: generators and acceptance tooling.
- `projects/`: active environment project sources and project state.
- `evidence/`: deliberately selected reports and rendered PNG evidence.
- `manifests/`: runtime artifact names and checksums; binaries are not committed.

## Security

The tracked `server.properties` must keep `management-server-secret` and all
password fields empty. Production secrets and Visual Probe session tokens are
runtime-only data and must never be committed.

The tracked HeadlessMC offline player name and UUID are public example values.
A deployment must replace them with its own stable identity outside Git and
grant permissions only to that deployment identity.
