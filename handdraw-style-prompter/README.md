# Handdraw Style Prompter — ChatGPT / Codex Adaptation

Personal OpenAI-compatible adaptation based on:

https://github.com/yang0/handraw-style

Original author: yang0

## Local changes

- Reorganized the original repository into a self-contained Skill.
- Supports style numbers `001–261`.
- Moved image/style resources inside the Skill root.
- Removed machine-specific absolute paths.
- Added portable relative asset resolution.
- Added `style_asset_paths.py` because the upstream repository references this module but does not currently include it.
- Renamed the upstream validation script because it references missing upstream modules.
- Removed hard dependencies on Codex-only browser calls and surface-specific image parameters.
- Added graceful fallback behavior for ChatGPT/Codex runtimes that cannot attach bundled reference images.
- Verified the core structure for prompt generation, style-index lookup, model-capability resolution, and numbered reference-image resolution.

This copy is maintained for personal/private use.
