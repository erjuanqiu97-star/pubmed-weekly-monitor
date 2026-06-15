from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from Bio import Entrez

from .classify import classify_article, classify_journal_priority


@dataclass
class PubMedRecord:
    pmid: str
    title: str
    journal: str
    publication_date: str
    authors: str
    abstract: str
    doi: str
    pubmed_url: str
    chinese_title: str = ""
    chinese_abstract_summary: str = ""
    matched_keyword_groups: set[str] = field(default_factory=set)
    journal_priority: str = "normal"
    article_category: str = "Original article"
    translation_status: str = "not requested"

    def to_row(self) -> dict[str, str]:
        return {
            "PMID": self.pmid,
            "Title": self.title,
            "Journal": self.journal,
            "Publication date": self.publication_date,
            "Authors": self.authors,
            "Abstract": self.abstract,
            "Chinese title": self.chinese_title,
            "Chinese abstract summary": self.chinese_abstract_summary,
            "DOI": self.doi,
            "PubMed URL": self.pubmed_url,
            "Matched keyword group": "; ".join(sorted(self.matched_keyword_groups)),
            "Journal priority": self.journal_priority,
            "Article category": self.article_category,
            "Translation status": self.translation_status,
        }


def configure_entrez(email: str, tool: str) -> None:
    if email:
        Entrez.email = email
    Entrez.tool = tool


def search_pubmed(
    keyword_groups: dict[str, list[str]],
    fields: list[str],
    start_date: date,
    end_date: date,
    date_type: str,
    retmax_per_group: int,
    journal_whitelist: set[str],
) -> list[PubMedRecord]:
    records_by_pmid: dict[str, PubMedRecord] = {}

    for group_name, terms in keyword_groups.items():
        query = build_group_query(terms, fields)
        pmids = esearch_pmids(
            query=query,
            start_date=start_date,
            end_date=end_date,
            date_type=date_type,
            retmax=retmax_per_group,
        )
        new_pmids = [pmid for pmid in pmids if pmid not in records_by_pmid]
        fetched_records = fetch_pubmed_records(new_pmids, journal_whitelist)

        for pmid in pmids:
            if pmid in records_by_pmid:
                records_by_pmid[pmid].matched_keyword_groups.add(group_name)

        for record in fetched_records:
            record.matched_keyword_groups.add(group_name)
            records_by_pmid[record.pmid] = record

    return sorted(
        records_by_pmid.values(),
        key=lambda record: (record.journal_priority != "high-priority", record.publication_date, record.title),
    )


def build_group_query(terms: list[str], fields: list[str]) -> str:
    clauses = []
    for term in terms:
        term = term.strip()
        if not term:
            continue
        if "[" in term and "]" in term:
            clauses.append(term)
            continue
        field_clauses = [f'"{term}"[{field}]' for field in fields]
        clauses.append("(" + " OR ".join(field_clauses) + ")")
    if not clauses:
        raise ValueError("Cannot build a PubMed query from an empty term list")
    return "(" + " OR ".join(clauses) + ")"


def esearch_pmids(
    query: str,
    start_date: date,
    end_date: date,
    date_type: str,
    retmax: int,
) -> list[str]:
    with Entrez.esearch(
        db="pubmed",
        term=query,
        retmax=retmax,
        sort="pub date",
        datetype=date_type,
        mindate=start_date.strftime("%Y/%m/%d"),
        maxdate=end_date.strftime("%Y/%m/%d"),
    ) as handle:
        result = Entrez.read(handle)
    return [str(pmid) for pmid in result.get("IdList", [])]


def fetch_pubmed_records(pmids: list[str], journal_whitelist: set[str]) -> list[PubMedRecord]:
    if not pmids:
        return []

    with Entrez.efetch(db="pubmed", id=",".join(pmids), rettype="abstract", retmode="xml") as handle:
        response = Entrez.read(handle)

    records = []
    for article in response.get("PubmedArticle", []):
        record = parse_pubmed_article(article, journal_whitelist)
        if record:
            records.append(record)
    return records


def parse_pubmed_article(article: dict[str, Any], journal_whitelist: set[str]) -> PubMedRecord | None:
    citation = article.get("MedlineCitation", {})
    pmid = str(citation.get("PMID", "")).strip()
    if not pmid:
        return None

    article_data = citation.get("Article", {})
    journal_data = article_data.get("Journal", {})
    journal = str(journal_data.get("Title") or journal_data.get("ISOAbbreviation") or "").strip()
    publication_types = [str(item) for item in article_data.get("PublicationTypeList", [])]

    record = PubMedRecord(
        pmid=pmid,
        title=clean_text(article_data.get("ArticleTitle", "")),
        journal=journal,
        publication_date=parse_publication_date(journal_data),
        authors=parse_authors(article_data.get("AuthorList", [])),
        abstract=parse_abstract(article_data.get("Abstract", {})),
        doi=parse_doi(article_data, article.get("PubmedData", {})),
        pubmed_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        journal_priority=classify_journal_priority(journal, journal_whitelist),
        article_category=classify_article(publication_types),
    )
    return record


def clean_text(value: Any) -> str:
    return " ".join(str(value).replace("\n", " ").split())


def parse_publication_date(journal_data: dict[str, Any]) -> str:
    pub_date = journal_data.get("JournalIssue", {}).get("PubDate", {})
    if not pub_date:
        return ""
    year = str(pub_date.get("Year", "")).strip()
    month = str(pub_date.get("Month", "")).strip()
    day = str(pub_date.get("Day", "")).strip()
    medline_date = str(pub_date.get("MedlineDate", "")).strip()
    parts = [part for part in [year, month, day] if part]
    return " ".join(parts) if parts else medline_date


def parse_authors(authors: list[Any]) -> str:
    names = []
    for author in authors:
        if not isinstance(author, dict):
            continue
        collective_name = author.get("CollectiveName")
        if collective_name:
            names.append(str(collective_name))
            continue
        last_name = str(author.get("LastName", "")).strip()
        initials = str(author.get("Initials", "")).strip()
        full_name = " ".join(part for part in [last_name, initials] if part)
        if full_name:
            names.append(full_name)
    return "; ".join(names)


def parse_abstract(abstract_data: dict[str, Any]) -> str:
    abstract_text = abstract_data.get("AbstractText", []) if isinstance(abstract_data, dict) else []
    parts = []
    for item in abstract_text:
        label = getattr(item, "attributes", {}).get("Label")
        text = clean_text(item)
        if not text:
            continue
        if label:
            parts.append(f"{label}: {text}")
        else:
            parts.append(text)
    return "\n".join(parts)


def parse_doi(article_data: dict[str, Any], pubmed_data: dict[str, Any]) -> str:
    for item in article_data.get("ELocationID", []):
        if str(getattr(item, "attributes", {}).get("EIdType", "")).casefold() == "doi":
            return clean_text(item)

    article_ids = pubmed_data.get("ArticleIdList", []) if isinstance(pubmed_data, dict) else []
    for article_id in article_ids:
        if str(getattr(article_id, "attributes", {}).get("IdType", "")).casefold() == "doi":
            return clean_text(article_id)
    return ""
