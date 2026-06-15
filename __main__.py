from __future__ import annotations

import argparse
import sys

from .config import load_config, load_journal_whitelist
from .pubmed_client import configure_entrez, search_pubmed
from .report import write_outputs
from .translate import translate_records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a weekly PubMed literature report.")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config.yaml. Default: config.yaml",
    )
    args = parser.parse_args(argv)

    config = load_config(args.config)
    if not config.ncbi_email or config.ncbi_email == "your.email@example.com":
        print(
            "Warning: Set NCBI_EMAIL or update ncbi.email in config.yaml before regular use.",
            file=sys.stderr,
        )

    journal_whitelist = load_journal_whitelist(config.journal_whitelist_path)
    configure_entrez(config.ncbi_email, config.ncbi_tool)

    records = search_pubmed(
        keyword_groups=config.keyword_groups,
        fields=config.fields,
        start_date=config.search_window.start_date,
        end_date=config.search_window.end_date,
        date_type=config.search_window.date_type,
        retmax_per_group=config.retmax_per_group,
        journal_whitelist=journal_whitelist,
    )
    translate_records(records, config.translation)
    write_outputs(records, config.outputs.report_md, config.outputs.results_xlsx)

    print(f"Generated {config.outputs.report_md}")
    print(f"Generated {config.outputs.results_xlsx}")
    print(f"Records: {len(records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
