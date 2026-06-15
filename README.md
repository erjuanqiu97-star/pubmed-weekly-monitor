# PubMed Weekly Literature Monitor

This project searches PubMed every week for new papers related to pulmonary fibrosis, inhalation delivery, inhalation formulations, inhalable microspheres, inhalable nanoparticles, liposomes, LNPs, mRNA delivery, and pulmonary delivery.

It generates:

- `outputs/weekly_pubmed_report.md`
- `outputs/weekly_pubmed_results.xlsx`

The journal priority list is maintained locally in `journal_whitelist.yaml`. No paid JCR, Web of Science, or Scopus API is used.

## Local Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Set your NCBI email. NCBI recommends identifying yourself when using E-utilities:

```bash
set NCBI_EMAIL=your.email@example.com
```

On macOS or Linux:

```bash
export NCBI_EMAIL=your.email@example.com
```

Run the monitor:

```bash
python -m pubmed_monitor --config config.yaml
```

## Chinese Translation

The report can add a Chinese title and a concise Chinese abstract summary for each article.

This project uses MyMemory by default because it can run without an API key. It is convenient for automated weekly monitoring, but translation quality may be lower than DeepL for difficult scientific prose.

The default configuration is:

```yaml
translation:
  provider: mymemory
  endpoint: https://api.mymemory.translated.net/get
  langpair: en|zh-CN
```

MyMemory limits each request segment, so the script automatically splits long abstract summaries and merges the translated result.

For higher-quality scientific translation, you can switch back to DeepL if you later obtain an API key:

```yaml
translation:
  provider: deepl
  endpoint: https://api-free.deepl.com/v2/translate
```

Then set:

```bash
set DEEPL_AUTH_KEY=your_deepl_api_key
```

On macOS or Linux:

```bash
export DEEPL_AUTH_KEY=your_deepl_api_key
```

If you use DeepL Pro API, change the endpoint to:

```yaml
translation:
  endpoint: https://api.deepl.com/v2/translate
```

## Email Delivery

GitHub Actions does not email the generated report by default. The workflow now includes an optional email step.

For Gmail, create an app password, then add these repository secrets:

```text
SMTP_USER      your Gmail address
SMTP_PASSWORD  Gmail app password
REPORT_TO      recipient email address
```

The default SMTP settings in `config.yaml` are:

```yaml
email:
  smtp_host: smtp.gmail.com
  smtp_port: 587
```

If these secrets are missing, the workflow still generates and uploads the report artifact, but skips email sending.

## Configuration

Edit `config.yaml` to change:

- Keyword groups
- PubMed search fields
- Search time range
- Output paths
- NCBI email fallback

By default, the script searches the most recent 7 days by PubMed publication date.

To use fixed dates, replace `days: 7` with:

```yaml
start_date: 2026-06-01
end_date: 2026-06-07
```

Edit `journal_whitelist.yaml` to update high-priority journals.

## Output Fields

The Excel output includes:

- PMID
- Title
- Journal
- Publication date
- Authors
- Abstract
- Chinese title
- Chinese abstract summary
- DOI
- PubMed URL
- Matched keyword group
- Journal priority
- Article category
- Translation status

## Classification

- Records from journals in `journal_whitelist.yaml` are marked as `high-priority`.
- PubMed records with publication type containing `Review` are classified as `Review`.
- All other records are classified as `Original article`.
- PMID is used for deduplication. If a paper matches multiple keyword groups, the groups are combined in `Matched keyword group`.

## GitHub Actions

The workflow in `.github/workflows/weekly_pubmed.yml` runs every Monday at `06:00 UTC` and can also be triggered manually.

Add `NCBI_EMAIL` as a repository secret for scheduled runs.

Add `SMTP_USER`, `SMTP_PASSWORD`, and `REPORT_TO` as repository secrets if you want scheduled runs to email the report.

For detailed setup steps, see `GITHUB_ACTIONS_EMAIL_SETUP.md`.
