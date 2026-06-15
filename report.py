from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from .pubmed_client import PubMedRecord


REQUIRED_COLUMNS = [
    "PMID",
    "Title",
    "Journal",
    "Publication date",
    "Authors",
    "Abstract",
    "Chinese title",
    "Chinese abstract summary",
    "DOI",
    "PubMed URL",
    "Matched keyword group",
    "Journal priority",
    "Article category",
    "Translation status",
]


def write_outputs(records: list[PubMedRecord], report_md: Path, results_xlsx: Path) -> None:
    report_md.parent.mkdir(parents=True, exist_ok=True)
    results_xlsx.parent.mkdir(parents=True, exist_ok=True)

    rows = [record.to_row() for record in records]
    dataframe = pd.DataFrame(rows, columns=REQUIRED_COLUMNS)
    dataframe.to_excel(results_xlsx, index=False)

    report_md.write_text(render_markdown_report(records), encoding="utf-8")


def render_markdown_report(records: list[PubMedRecord]) -> str:
    high_priority = [record for record in records if record.journal_priority == "high-priority"]
    reviews = [record for record in records if record.article_category == "Review"]
    originals = [record for record in records if record.article_category == "Original article"]

    lines = [
        "# Weekly PubMed Report",
        "",
        f"Generated date: {date.today().isoformat()}",
        f"Total records: {len(records)}",
        f"High-priority journal records: {len(high_priority)}",
        f"Reviews: {len(reviews)}",
        f"Original articles: {len(originals)}",
        "",
    ]

    lines.extend(render_section("Reviews", reviews))
    lines.extend(render_section("Original Articles", originals))
    return "\n".join(lines).rstrip() + "\n"


def render_section(title: str, records: list[PubMedRecord]) -> list[str]:
    lines = [f"## {title}", ""]
    if not records:
        return lines + ["No records found.", ""]

    for index, record in enumerate(records, start=1):
        lines.extend(
            [
                f"### {index}. {record.title or 'Untitled'}",
                "",
                f"- PMID: [{record.pmid}]({record.pubmed_url})",
                f"- Journal: {record.journal or 'N/A'}",
                f"- Publication date: {record.publication_date or 'N/A'}",
                f"- Authors: {record.authors or 'N/A'}",
                f"- DOI: {record.doi or 'N/A'}",
                f"- Matched keyword group: {'; '.join(sorted(record.matched_keyword_groups)) or 'N/A'}",
                f"- Journal priority: {record.journal_priority}",
                f"- Article category: {record.article_category}",
                f"- Translation status: {record.translation_status}",
                "",
                "**Chinese title**",
                "",
                record.chinese_title or "Chinese title was not generated.",
                "",
                "**Chinese abstract summary**",
                "",
                record.chinese_abstract_summary or "Chinese abstract summary was not generated.",
                "",
                "**Abstract**",
                "",
                record.abstract or "No abstract available.",
                "",
            ]
        )
    return lines
