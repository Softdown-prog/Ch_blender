"""Executable-side backend identity; never changes the Blender version contract."""
import json
from pathlib import Path
OFFICIAL = 'official_4_2_3'
LEGACY = 'legacy_cpu_4_2_3'
def identify_backend(executable):
    marker = Path(executable).parent / 'ch-legacy-build.json'
    if not marker.is_file():
        return OFFICIAL
    try:
        info = json.loads(marker.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as exc:
        raise ValueError('Invalid CH Legacy build marker') from exc
    if info.get('backend') != LEGACY or info.get('upstreamTag') != 'v4.2.3':
        raise ValueError('CH Legacy build marker does not match Blender 4.2.3')
    return LEGACY
