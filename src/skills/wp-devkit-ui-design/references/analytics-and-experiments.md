# Analytics and experiments

Instrument behavior only when the measurement is necessary and authorized. Contents: event design, privacy, validation, experiments, interpretation.

## Event design

- Taxonomy: stable `object_action` names, owner, trigger condition (the exact DOM or server boundary), properties, version, and a data dictionary. Fire once per intended user action (debounce, guard against repeated listeners, SPA re-renders and client navigation).
- Never collect secrets, free-text form content, passwords, payment data or direct identifiers as event properties. Hash or drop emails; avoid URL query strings with personal data.
- Funnels: define steps, activation and retention precisely, and the segment dimensions that are allowed.

## Privacy and consent (WordPress sites)

Confirm the legal basis and consent requirements for the audiences served (for example ePrivacy/GDPR for non-essential cookies or device identifiers in the EU/UK) with the site owner or counsel; this skill does not decide legal questions. Load analytics only after consent where required; honor Do Not Track/Global Privacy Control policy decisions the owner has made; document retention, processors and cross-border transfers. Keep staging and production data separate and exclude logged-in editors and bots.

## Validation of instrumentation

Test each event in a browser with network inspection: once per action, correct properties, absent after declined consent, correct under client navigation, correct with ad blockers (loss is expected and must be known). For server-side events confirm idempotency on retries.

## Experiments

Before launch record: hypothesis, eligible population, randomization unit (user, session, page), exposure event (logged only when the variant is actually seen), primary metric, guardrails (errors, performance, accessibility regressions), minimum duration and sample, stopping rule, holdout, rollout and rollback. Do not peek-and-stop. Caching layers can serve one variant to everyone; verify bucketing at the edge and in page cache.

## Interpretation limits

Correlation in analytics is descriptive; only a valid experiment supports a causal claim. Do not invent conversion or performance numbers. Report data freshness, sampling, missing/duplicate event rates, and which instrumentation boundaries are unverified.

## Sources

Research date: 2026-10-08. Sources: [Web Vitals measurement guidance](https://web.dev/articles/vitals), [GDPR consent basics (EDPB)](https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-052020-consent-under-regulation-2016679_en).
