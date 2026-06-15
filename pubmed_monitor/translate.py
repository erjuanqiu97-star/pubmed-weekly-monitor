from __future__ import annotations

import re
from dataclasses import dataclass

import requests

from .config import TranslationConfig
from .pubmed_client import PubMedRecord


@dataclass(frozen=True)
class TranslationTask:
    pmid: str
    field: str
    text: str


def translate_records(records: list[PubMedRecord], config: TranslationConfig) -> None:
    if not config.enabled:
        for record in records:
            record.translation_status = "disabled"
        return

    if config.provider not in {"deepl", "mymemory"}:
        for record in records:
            record.translation_status = f"unsupported provider: {config.provider}"
        return

    if config.provider == "deepl" and not config.auth_key:
        for record in records:
            record.translation_status = f"missing {config.auth_key_env}"
        return

    tasks = build_translation_tasks(records, config)
    if not tasks:
        for record in records:
            record.translation_status = "no text to translate"
        return

    try:
        if config.provider == "deepl":
            translations = translate_with_deepl(tasks, config)
        else:
            translations = translate_with_mymemory(tasks, config)
    except requests.RequestException as exc:
        for record in records:
            record.translation_status = f"translation failed: {exc}"
        return

    records_by_pmid = {record.pmid: record for record in records}
    for task, translated_text in zip(tasks, translations):
        record = records_by_pmid[task.pmid]
        if task.field == "title":
            record.chinese_title = translated_text
        elif task.field == "abstract_summary":
            record.chinese_abstract_summary = translated_text
        record.translation_status = f"translated by {config.provider}"


def build_translation_tasks(records: list[PubMedRecord], config: TranslationConfig) -> list[TranslationTask]:
    tasks: list[TranslationTask] = []
    for record in records:
        if record.title:
            tasks.append(TranslationTask(record.pmid, "title", record.title))
        summary = summarize_abstract(record.abstract, config.summary_sentences, config.max_summary_chars)
        if summary:
            tasks.append(TranslationTask(record.pmid, "abstract_summary", summary))
        elif record.title:
            record.translation_status = "title only: no abstract"
    return tasks


def translate_with_deepl(tasks: list[TranslationTask], config: TranslationConfig) -> list[str]:
    translated: list[str] = []
    for batch in chunk_tasks(tasks):
        response = requests.post(
            config.endpoint,
            headers={
                "Authorization": f"DeepL-Auth-Key {config.auth_key}",
                "Content-Type": "application/json",
            },
            json={
                "text": [task.text for task in batch],
                "source_lang": config.source_lang,
                "target_lang": config.target_lang,
                "preserve_formatting": True,
            },
            timeout=config.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        translated.extend(item.get("text", "") for item in payload.get("translations", []))
    return translated


def translate_with_mymemory(tasks: list[TranslationTask], config: TranslationConfig) -> list[str]:
    translated: list[str] = []
    for task in tasks:
        translated.append(translate_long_text_with_mymemory(task.text, config))
    return translated


def translate_long_text_with_mymemory(text: str, config: TranslationConfig) -> str:
    parts = []
    for chunk in chunk_text_for_mymemory(text):
        params = {
            "q": chunk,
            "langpair": config.langpair,
            "mt": "1",
        }
        if config.contact_email:
            params["de"] = config.contact_email
        response = requests.get(config.endpoint, params=params, timeout=config.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        parts.append(payload.get("responseData", {}).get("translatedText", ""))
    return " ".join(part for part in parts if part).strip()


def chunk_text_for_mymemory(text: str, max_bytes: int = 480) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    current: list[str] = []

    for word in words:
        candidate = " ".join(current + [word])
        if current and len(candidate.encode("utf-8")) > max_bytes:
            chunks.append(" ".join(current))
            current = [word]
        else:
            current.append(word)

    if current:
        chunks.append(" ".join(current))
    return chunks


def chunk_tasks(tasks: list[TranslationTask], max_chars: int = 25000, max_items: int = 40) -> list[list[TranslationTask]]:
    chunks: list[list[TranslationTask]] = []
    current: list[TranslationTask] = []
    current_chars = 0

    for task in tasks:
        text_length = len(task.text)
        if current and (len(current) >= max_items or current_chars + text_length > max_chars):
            chunks.append(current)
            current = []
            current_chars = 0
        current.append(task)
        current_chars += text_length

    if current:
        chunks.append(current)
    return chunks


def summarize_abstract(abstract: str, sentence_count: int, max_chars: int) -> str:
    cleaned = " ".join(abstract.split())
    if not cleaned:
        return ""

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    summary = " ".join(sentences[:sentence_count]).strip()
    if len(summary) <= max_chars:
        return summary
    return summary[:max_chars].rsplit(" ", 1)[0].strip() + "..."
