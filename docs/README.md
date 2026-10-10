# WordPress DevKit user guides

Start with [the field guide](index.html) or [the guide library](guides/index.html). This directory is a static HTML learning site for users of the Claude, ChatGPT, Codex and Antigravity skill pack.

## Learning path

- [Your first review](guides/quick-start.html)
- [Installation, updates, removal and recovery](guides/installation.html)
- [Doctor and evidence reports](guides/doctor-and-reports.html)
- [Review to fix](guides/review-to-fix.html)
- [Release checklist](guides/release-checklist.html)
- [Questions and troubleshooting](guides/faq.html)
- [All 20 specialist guides](guides/index.html)
- [All 41 Claude commands](commands.html)

## Read it online

The guides are published with GitHub Pages at <https://ehsanenaloo.github.io/wordpress-devkit/> (repository **Settings → Pages → Deploy from a branch → `main` / `/docs`**). GitHub shows the HTML source when you browse the files here.

## Local preview

From the repository root:

```sh
python -m http.server 8765 --bind 127.0.0.1 --directory docs
```

Open http://127.0.0.1:8765/ in your browser and stop the server with Ctrl+C. The guides need no build step or external services. They work without JavaScript; enable it for search and copy buttons.

## Maintenance

Keep skill names, commands and examples aligned with the skills in `src/skills/` and the installer and report tooling. Do not imply broader runtime coverage than the project's checks support. All content is English. The site's prose, HTML, CSS and JavaScript are original WordPress DevKit material; see [attribution](ATTRIBUTION.md) and the [MIT License](../LICENSE).
