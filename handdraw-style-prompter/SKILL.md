---
name: handdraw-style-prompter
description: Turn a 001–261 hand-drawn style number and image theme into bilingual prompts, or explicitly generate an image using the best available style-reference strategy for the current OpenAI surface.
---

# Hand-drawn Style Prompter

Default to prompt generation only. Generate or render an image only when the user explicitly asks for an image, preview, render, or generation.

## Inputs

Require a style number (`001`–`261`) and a theme. Accept optional aspect ratio, subject constraints, and text requirements.

- If the style number is missing or invalid, ask for a valid number; never invent one.
- Do not add an aspect ratio, copy, subject, or other constraint the user did not supply.
- `references/styles.json` is the runtime style index. `styles_200_reorganized.md` is the authoritative source and should be rebuilt into the derived index with `python scripts/build_library.py` after edits.

## Prompt-only mode

For a valid request, return four compact parts:

1. Selected style: number and `generation_name`.
2. Chinese prompt beginning with `风格名称：#{number} · {generation_name}。` and including the indexed `reference` as `参考作者/风格名称：...`.
3. English prompt beginning with `Style name: #{number} · {generation_name}.` and including the same indexed reference as `Reference author/style name: ...`.
4. One brief note that the prompt can be used in an image AI and that generation is controlled by that AI.

For ordinary prompt-only requests:

- Describe only the user's theme and explicit constraints.
- Do not append `traits`, fixed style anchors, generic quality language, generic composition advice, negative prompts, or invented details.
- Treat the indexed reference as a lookup label, not as a factual claim about the person and not as a reason to infer model capability.
- Do not use fame, life status, or popularity as a proxy for model behavior.

## Explicit image-generation mode

Use the native image-generation capability actually available on the current surface. Do not assume a particular tool name, MCP function, or argument name.

### 1. Resolve the preferred style strategy

If the current image model or model family is known, resolve it against `references/model_capabilities.json`. If it is not known, treat it as `unknown`; never guess a model identifier.

`python scripts/resolve_reference.py --model <model> --style <number>` may be used for a deterministic preference check. Its `activation_source` is one of:

- `name+style`: use the indexed reference name + generated style name + user's theme; no reference image.
- `name+style+traits`: additionally use only positive, concrete visible traits from the index; no reference image.
- `reference-image`: prefer the numbered reference asset when the current surface can actually attach a bundled image to image generation.

Filter trait clauses containing `避免`, `不要`, or `不准`. Do not copy the full traits field mechanically.

### 2. Reference-image fallback must be surface-aware

Resolve the numbered asset from `images/individual/{bucket}/`. Prefer `{number}_grid.jpg` when present; otherwise use `{number}.png`.

If the current runtime can attach that bundled asset to its image-generation request, attach it using the runtime's supported mechanism. Never invent or hard-code a parameter name such as `referenced_image_paths`.

If the current runtime cannot pass bundled Skill images into image generation:

- do not pretend a reference image was attached;
- fall back to `name+style+traits` when positive traits are available;
- otherwise use `name+style` only;
- do not substitute an unrelated image.

When a numbered reference image is actually attached, add this reference-isolation instruction to the generation prompt:

`所附图片仅用于参考画风。只提取参考图的风格特征，例如线条、笔触、媒介、材质、色彩倾向和整体视觉语言；不要使用、复制或延续参考图中的任何主体、人物、动物、服装、道具、动作、姿态、场景、背景、构图、布局、文字或故事。最终画面内容完全以用户提供的主题为准。`

English equivalent:

`Use the attached image only as a style reference. Extract only its stylistic qualities, such as linework, brushwork, medium, material texture, color tendencies, and overall visual language. Do not use, copy, or carry over any subject, person, animal, clothing, prop, action, pose, setting, background, composition, layout, text, or story from the reference image. The user's written theme is the sole source for the image content.`

The user's theme remains the sole source for subjects and narrative.

## Gallery

`gallery/index.html` is the bundled numbered gallery.

- Do not open it automatically when the Skill starts.
- If the user asks to browse or choose a style visually, open the bundled gallery only when the current surface exposes a supported way to open local Skill resources.
- If that capability is unavailable, mention the bundled path `gallery/index.html` and continue without blocking the user's task.
- Never call a Codex-only browser function merely because this Skill is running in ChatGPT.

## Portability

This Skill is intended to work in both ChatGPT and Codex.

- Use only tools and capabilities actually exposed by the current runtime.
- Never assume `mcp__codex_app__open_in_codex`, `referenced_image_paths`, or any other surface-specific API exists.
- A missing optional capability must degrade gracefully to the prompt-only or text-style path instead of failing the whole Skill.

## Utilities

- Rebuild derived style data and gallery: `python scripts/build_library.py`
- Split contact sheets into numbered images: `python scripts/split_contact_sheets.py`
- Produce a deterministic prompt draft: `python scripts/prompt_style.py --style 18 --theme "秋天的第一杯奶茶"`
- Resolve preferred image-reference strategy: `python scripts/resolve_reference.py --model <model> --style 18`

The CLI utilities are convenience checks. In normal conversation, write natural bilingual prompts rather than mechanically echoing their templates.
