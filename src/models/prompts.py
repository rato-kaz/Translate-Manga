"""
Prompt building utilities.
"""

from typing import Dict, List, Optional, Sequence

from src.utils.constants import LANGUAGE_NAMES, TRANSLATION_SKIP_PATTERNS


def build_vlm_prompt(texts: Sequence[str]) -> str:
    base_prompt = (
        "You are a visual storytelling assistant that describes manga panels. "
        "Describe the given manga panel in one or two sentences. "
        "Focus on the characters, their actions, emotions, and any visible dialogue. "
        "Avoid generic phrases like 'in a manga style'. Use natural prose suitable for a novel or screenplay. "
        "Do not explain anything else. Only output the description."
    )
    combined_text = "\n".join(filter(None, texts)).strip()
    if combined_text:
        base_prompt += f"\n\nThe following text appears in the panel: '{combined_text}'."
    return base_prompt


def build_llm_system_prompt() -> str:
    return (
        "You are a professional manga translator with deep understanding of Japanese culture, "
        "manga storytelling, and character nuances. Your translations must:\n"
        "1. Preserve the character's personality and speech style\n"
        "2. Match the tone and context of the scene\n"
        "3. Use appropriate formality level based on character relationships\n"
        "4. Maintain cultural context and manga-specific expressions\n"
        "5. Keep dialogue natural and readable in the target language\n"
        "6. Consider the panel description to understand the scene context\n"
        "7. Preserve emotional tone (excited, sad, angry, etc.)\n\n"
        "Provide ONLY the translation, without explanations or additional text."
    )


def build_llm_user_prompt(text: str, source_lang: str, target_lang: str, context: Optional[Dict] = None) -> str:
    source_name = LANGUAGE_NAMES.get(source_lang, source_lang)
    target_name = LANGUAGE_NAMES.get(target_lang, target_lang)
    user_prompt_parts = [f"Translate the following {source_name} text to {target_name}."]
    if context:
        context_parts = _extract_context_parts(context)
        if context_parts:
            user_prompt_parts.append("\nContext Information:")
            user_prompt_parts.extend([f"- {part}" for part in context_parts])
    user_prompt_parts.append(f"\nText to translate:\n{text}")
    return "\n".join(user_prompt_parts)


def _extract_context_parts(context: Dict) -> List[str]:
    parts = []
    if context.get("chapter") is not None:
        parts.append(f"Chapter: {context['chapter']}")
    if context.get("page") is not None:
        parts.append(f"Page: {context['page']}")
    if context.get("panel") is not None:
        parts.append(f"Panel: {context['panel']}")
    if context.get("bubble") is not None:
        parts.append(f"Bubble: {context['bubble']}")
    speaker = context.get("speaker")
    if speaker:
        speaker_type = speaker.get("type", "unknown")
        if speaker_type == "character":
            parts.append(f"Speaker: {speaker.get('character_name', 'Unknown')}")
        elif speaker_type == "narrator":
            parts.append("Speaker: Narrator")
    caption = context.get("caption")
    if caption:
        parts.append(f"Panel Description: {caption}")
    return parts


def clean_translation(translation: str) -> str:
    if not translation:
        return ""
    lines = translation.split("\n")
    cleaned = []
    for line in lines:
        line = line.strip()
        if any(skip in line.lower() for skip in TRANSLATION_SKIP_PATTERNS):
            continue
        if line:
            cleaned.append(line)
    return " ".join(cleaned).strip()

