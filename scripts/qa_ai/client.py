"""DeepSeek transport and JSON decoding."""
import json
import os

import requests

API_URL = "https://api.deepseek.com/chat/completions"
# DeepSeek retired V4-Flash on 10 September 2026. The supported rolling Flash
# alias now serves V4.1-Flash. DEEPSEEK_MODEL allows an explicit override if
# DeepSeek exposes a pinned model identifier in future.
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-flash")
# Hardcoded operational switch. Keep this False to disable all DeepSeek-backed
# checks without changing filter definitions or command-line invocations.
# Set it back to True when AI review should be re-enabled.
DEEPSEEK_AI_CHECKS_ENABLED = True

def parse_model_json(model_output):
    """Parse JSON, tolerating accidental Markdown fences."""

    text = model_output.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    return json.loads(text)

def request_review(system_prompt, user_prompt, api_key):
    """Send a review request, retrying once if the model returns invalid JSON."""

    if not DEEPSEEK_AI_CHECKS_ENABLED:
        raise RuntimeError(
            "DeepSeek AI checks are disabled by DEEPSEEK_AI_CHECKS_ENABLED = False."
        )
    payload = {
        "model": MODEL,
        "thinking": {"type": "disabled"},
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    last_error = None
    for attempt in range(2):
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=180,
        )

        response.raise_for_status()
        result = response.json()
        model_output = result["choices"][0]["message"]["content"]
        try:
            return parse_model_json(model_output)
        except json.JSONDecodeError as error:
            last_error = error
            if attempt == 0:
                payload["messages"] = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                    {
                        "role": "user",
                        "content": (
                            "Your previous response was not valid JSON. "
                            "Return the review again as strictly valid JSON only. "
                            "Ensure all strings are correctly escaped and all "
                            "commas, quotes, brackets and braces are valid."
                        ),
                    },
                ]
    raise last_error
