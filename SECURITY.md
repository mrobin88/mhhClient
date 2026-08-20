# Security Policy

## Reporting a vulnerability

Do not open a public issue containing vulnerability details, credentials, production
URLs that are not already public, or client information.

Report security concerns privately to the repository owner or the security contact
listed by the organization. Include:

- A concise description and affected component
- Reproduction steps using synthetic data
- Expected impact
- Any suggested mitigation

Do not access, download, alter, or retain real client data while investigating.

## Secrets and data

- Never commit `.env` files, encryption keys, database credentials, API keys, or
  Azure connection strings.
- Use synthetic clients and documents in development.
- Production SSN encryption keys must be stored in managed application settings or
  Azure Key Vault and must not be reused locally.
- Public document-upload links are bearer credentials. Do not log or publish their
  full tokens.
