# GitHub Actions Email Setup

This project already includes a weekly GitHub Actions workflow:

```text
.github/workflows/weekly_pubmed.yml
```

It runs every Monday at `06:00 UTC`, generates the PubMed report, uploads the report as an artifact, and can email the Markdown and Excel files if the required repository secrets are configured.

## 1. Push This Project To GitHub

GitHub Actions only runs inside a GitHub repository. A local folder alone will not trigger the weekly schedule.

After creating a GitHub repository, push this project to the repository default branch, usually `main`.

## 2. Add Repository Secrets

Open your GitHub repository page, then go to:

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

Add these secrets:

```text
NCBI_EMAIL      Your email address for NCBI E-utilities
SMTP_USER       The email account used to send reports
SMTP_PASSWORD   SMTP password or Gmail app password
REPORT_TO       The email address that should receive reports
```

Example values:

```text
NCBI_EMAIL      erjuanqiu97@gmail.com
SMTP_USER       erjuanqiu97@gmail.com
SMTP_PASSWORD   your Gmail app password
REPORT_TO       erjuanqiu97@gmail.com
```

Do not write real passwords into `config.yaml`, README files, or source code.

## 3. Gmail App Password

If you use Gmail as the sender:

1. Enable 2-Step Verification for the Google account.
2. Create a Gmail app password.
3. Use the app password as `SMTP_PASSWORD`.

The normal Gmail login password usually will not work for SMTP automation.

The default SMTP config is:

```yaml
email:
  enabled: true
  smtp_host: smtp.gmail.com
  smtp_port: 587
  smtp_user_env: SMTP_USER
  smtp_password_env: SMTP_PASSWORD
  report_to_env: REPORT_TO
  report_from_env: SMTP_USER
```

## 4. Test Manually

After adding secrets, open:

```text
Actions -> Weekly PubMed Monitor -> Run workflow
```

A successful run should show:

```text
Generate weekly report
Email report
Upload report artifacts
```

If `Email report` says secrets are missing, check that the secret names exactly match:

```text
SMTP_USER
SMTP_PASSWORD
REPORT_TO
```

## 5. Important Notes

- Scheduled workflows only run after the workflow file is pushed to GitHub.
- Scheduled workflows run on the default branch.
- GitHub cron uses UTC time, so `06:00 UTC` is about `08:00` in Germany during summer time and `07:00` during winter time.
- If the repository is private or newly created, confirm that GitHub Actions is enabled in the repository settings.
- Even if email sending fails, the workflow should still upload `weekly_pubmed_report.md` and `weekly_pubmed_results.xlsx` as artifacts.
