from __future__ import annotations

from llama_cpp import Llama


PROMPT_TEMPLATE = """You extract broader theological concepts for Bible verse lookup.
Rules:
- Output only concepts or themes
- Prefer broader spiritual ideas over literal wording
- Include related doctrinal or pastoral themes when strongly implied
- Use 3 to 6 items
- Comma-separated only
- No preamble
- No sentence
- No explanation

Examples:
faith, courage, fear of God
peace, anxiety, trust, prayer
love, salvation, grace, atonement
forgetfulness, remembrance of God, covenant unfaithfulness

Text:
{transcript}
"""


class KeywordExtractor:
    def __init__(
        self,
        model_path: str,
        n_ctx: int = 2048,
        max_tokens: int = 10,
        n_gpu_layers: int = 0,
        verbose: bool = False,
    ) -> None:
        self.max_tokens = max_tokens
        self.model = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            verbose=verbose,
        )

    def extract(self, transcript: str) -> str:
        prompt = PROMPT_TEMPLATE.format(transcript=transcript.strip())
        response = self.model.create_completion(
            prompt=prompt,
            max_tokens=self.max_tokens,
            temperature=0.1,
            top_p=0.9,
            stop=["\n"],
            echo=False,
        )
        text = response["choices"][0]["text"].strip()
        return _normalize_keywords(text or transcript.strip())


def _normalize_keywords(text: str) -> str:
    prefixes = ("keywords:", "themes:", "concepts:", "theological themes:")
    normalized = text.strip().replace("\n", ", ")
    lowered = normalized.lower()
    for prefix in prefixes:
        if lowered.startswith(prefix):
            normalized = normalized[len(prefix) :].strip()
            break
    parts = [part.strip(" ,.;:-") for part in normalized.split(",")]
    parts = [part for part in parts if part]
    cleaned_parts: list[str] = []
    for part in parts:
        words = part.split()
        if len(words) > 4:
            continue
        if part.lower().startswith(("i ", "i am ", "this ", "the text ")):
            continue
        cleaned_parts.append(part)
    if cleaned_parts:
        return ", ".join(cleaned_parts[:5])
    return ", ".join(parts)
