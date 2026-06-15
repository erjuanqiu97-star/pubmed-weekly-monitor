from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any
import os

import yaml


@dataclass(frozen=True)
class OutputConfig:
    report_md: Path
    results_xlsx: Path


@dataclass(frozen=True)
class TranslationConfig:
    enabled: bool
    provider: str
    auth_key_env: str
    auth_key: str
    endpoint: str
    langpair: str
    contact_email: str
    source_lang: str
    target_lang: str
    summary_sentences: int
    max_summary_chars: int
    timeout_seconds: int


@dataclass(frozen=True)
class SearchWindow:
    start_date: date
    end_date: date
    date_type: str


@dataclass(frozen=True)
class AppConfig:
    config_path: Path
    ncbi_email: str
    ncbi_tool: str
    keyword_groups: dict[str, list[str]]
    fields: list[str]
    retmax_per_group: int
    search_window: SearchWindow
    outputs: OutputConfig
    journal_whitelist_path: Path
    translation: TranslationConfig


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    return data


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path).resolve()
    root = config_path.parent
    raw = load_yaml(config_path)

    ncbi = raw.get("ncbi", {})
    email_env = str(ncbi.get("email_env", "NCBI_EMAIL"))
    ncbi_email = os.getenv(email_env) or str(ncbi.get("email", "")).strip()
    ncbi_tool = str(ncbi.get("tool", "weekly-pubmed-monitor")).strip()

    search = raw.get("search", {})
    keyword_groups = search.get("keyword_groups", {})
    if not isinstance(keyword_groups, dict) or not keyword_groups:
        raise ValueError("config.yaml must define search.keyword_groups")
    normalized_groups = {
        str(group): [str(term) for term in terms]
        for group, terms in keyword_groups.items()
        if terms
    }
    if not normalized_groups:
        raise ValueError("At least one keyword group must contain search terms")

    fields = [str(field) for field in search.get("fields", ["Title/Abstract"])]
    retmax_per_group = int(search.get("retmax_per_group", 200))
    date_type = str(search.get("date_type", "pdat"))
    search_window = _build_search_window(search, date_type)

    outputs = raw.get("outputs", {})
    report_md = root / outputs.get("report_md", "outputs/weekly_pubmed_report.md")
    results_xlsx = root / outputs.get("results_xlsx", "outputs/weekly_pubmed_results.xlsx")

    journals = raw.get("journals", {})
    journal_whitelist_path = root / journals.get("whitelist_file", "journal_whitelist.yaml")
    translation = _load_translation_config(raw.get("translation", {}))

    return AppConfig(
        config_path=config_path,
        ncbi_email=ncbi_email,
        ncbi_tool=ncbi_tool,
        keyword_groups=normalized_groups,
        fields=fields,
        retmax_per_group=retmax_per_group,
        search_window=search_window,
        outputs=OutputConfig(report_md=report_md, results_xlsx=results_xlsx),
        journal_whitelist_path=journal_whitelist_path,
        translation=translation,
    )


def load_journal_whitelist(path: str | Path) -> set[str]:
    raw = load_yaml(Path(path))
    journals = raw.get("high_priority_journals", [])
    if not isinstance(journals, list):
        raise ValueError("journal_whitelist.yaml must define high_priority_journals as a list")
    return {normalize_journal_name(str(journal)) for journal in journals}


def normalize_journal_name(name: str) -> str:
    return " ".join(name.casefold().replace("&", "and").split())


def _build_search_window(search: dict[str, Any], date_type: str) -> SearchWindow:
    today = date.today()
    if search.get("start_date") and search.get("end_date"):
        return SearchWindow(
            start_date=date.fromisoformat(str(search["start_date"])),
            end_date=date.fromisoformat(str(search["end_date"])),
            date_type=date_type,
        )

    days = int(search.get("days", 7))
    if days < 1:
        raise ValueError("search.days must be at least 1")
    return SearchWindow(
        start_date=today - timedelta(days=days),
        end_date=today,
        date_type=date_type,
    )


def _load_translation_config(raw: dict[str, Any]) -> TranslationConfig:
    auth_key_env = str(raw.get("auth_key_env", "DEEPL_AUTH_KEY"))
    return TranslationConfig(
        enabled=bool(raw.get("enabled", True)),
        provider=str(raw.get("provider", "deepl")).casefold(),
        auth_key_env=auth_key_env,
        auth_key=os.getenv(auth_key_env, "").strip(),
        endpoint=str(raw.get("endpoint", "https://api.mymemory.translated.net/get")).strip(),
        langpair=str(raw.get("langpair", "en|zh-CN")).strip(),
        contact_email=os.getenv(str(raw.get("contact_email_env", "NCBI_EMAIL")), "").strip(),
        source_lang=str(raw.get("source_lang", "EN")).strip(),
        target_lang=str(raw.get("target_lang", "ZH")).strip(),
        summary_sentences=max(1, int(raw.get("summary_sentences", 3))),
        max_summary_chars=max(100, int(raw.get("max_summary_chars", 1200))),
        timeout_seconds=max(5, int(raw.get("timeout_seconds", 30))),
    )
