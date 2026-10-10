# Acceptance checklist

Use the rows relevant to the change; report each as passed (with evidence), failed, or unexecuted. Contents: layout, interaction, content, system, evidence, what passing does not prove.

## Layout and parity

- Editor and front end agree on typography, widths and spacing (compare computed values).
- No unintended horizontal scroll at 320, 360, 768, 1280 px and at 200% and 400% zoom.
- Long headings, missing images, empty lists, long translations and validation errors remain usable.

## Interaction and accessibility

- Navigation, dialogs, forms and menus work by keyboard with visible `:focus-visible`; focus is not hidden by sticky UI (WCAG 2.4.11); drag-only actions have an alternative (2.5.7).
- Pointer targets at least 24 by 24 CSS px or meet an exception (2.5.8).
- Contrast: text 4.5:1, large text and UI components 3:1, measured on actual pairings including hover/focus/disabled.
- Reduced motion, forced colors and (if shipped) dark mode behave.
- Automated scan (axe) run and results recorded; manual keyboard and screen-reader checks named explicitly.

## Content and locale

- RTL uses logical properties and sensible mixed-direction text; plural, long-string and mixed-script checks pass for supported locales.
- Labels, help, errors, empty and success states exist and make sense out of context.

## System

- Token ownership, mappings, component states and migration impact are documented when a design system changes.
- Visual regression uses stable fixtures and an explicit browser/device matrix; baseline changes carry a recorded acceptance decision.
- Performance claims name lab vs field, page, build, conditions and date; thresholds LCP 2.5 s, INP 200 ms, CLS 0.1 at p75.
- Research and analytics claims are backed by sessions or validated events; otherwise labeled "not measured". Instrumentation has documented triggers, consent behavior and privacy boundaries; experiments define eligibility, exposure, metrics, guardrails and stopping rules.

## Evidence to record

Viewport and browser versions, locale/direction, screenshots (before/after), commands with exit codes, which assistive technology was actually used, and the list of checks not run.

## Passing does not prove

Real-user outcomes, screen-reader behavior beyond the tested combinations, performance in the field, behavior on devices outside the matrix, or legal compliance.

## Sources

Research date: 2026-10-08. Sources: [WCAG 2.2](https://www.w3.org/TR/WCAG22/), [Core Web Vitals thresholds](https://web.dev/articles/vitals), [WordPress accessibility handbook](https://make.wordpress.org/accessibility/handbook/).
