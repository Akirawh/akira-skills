# Handdraw Style Prompter — Local Adaptation

Personal Codex-compatible adaptation based on:

https://github.com/yang0/handraw-style

Original author: yang0

## Local changes

- Reorganized the original repository into a self-contained Skill.
- Moved image/style resources inside the Skill root.
- Removed machine-specific absolute paths.
- Added portable relative asset resolution.
- Added `style_asset_paths.py` because the upstream repository references this module but does not currently include it.
- Renamed the upstream validation script because it references missing upstream modules.
- Verified:
  - prompt generation
  - style index lookup
  - model capability resolution
  - numbered reference-image resolution

This copy is maintained for personal/private use.
