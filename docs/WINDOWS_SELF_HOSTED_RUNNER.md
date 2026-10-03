# CH Blender — Windows self-hosted runner

The CH Blender production workflow is configured to execute heavy Blender work on a Windows self-hosted GitHub Actions runner.

## Required runner labels

- `self-hosted`
- `Windows`
- `X64`

## PC setup

Register the machine from **Repository Settings > Actions > Runners > New self-hosted runner**, selecting Windows x64 and following the commands GitHub generates.

Install on the runner PC:

- Git
- Python
- Blender

Blender may be available through `PATH`. The workflow also checks common Blender Foundation installation folders.

## Execution contract

The workflow:

1. checks out this standalone CH Blender repository;
2. validates Git and Python;
3. resolves the local `blender.exe`;
4. exports `BLENDER_EXE` and `CH_BLENDER_EXE`;
5. validates the migrated CH Blender and Tycoon Photo Studio paths;
6. executes an optional CH Blender command supplied through `workflow_dispatch`;
7. inventories common render/output directories.

The existing `.github/actions/setup-ch-blender` action remains for Linux compatibility. It is intentionally not used by the Windows self-hosted workflow because it downloads a Linux Blender build and uses Linux system dependencies.

Heavy rendering therefore runs on the registered Windows PC rather than on a GitHub-hosted compute runner.
