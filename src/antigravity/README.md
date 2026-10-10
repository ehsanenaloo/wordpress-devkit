# WordPress DevKit for Google Antigravity

Use these 20 specialist skills to build, debug or review WordPress projects. Each skill includes its complete workflow, engineering contract, domain workbook and selected references. This is an instruction pack maintained by Ehsan Enaloo under the MIT License (see the `LICENSE` file in this folder).

## Install the plugin

Extract the archive first. The extracted `wp-devkit` directory contains the native Google manifest and `skills/` tree. Keep each complete skill folder together.

For Antigravity CLI, use the local plugin workflow documented by Google:

```sh
agy plugin install "C:\path\to\wp-devkit"
agy plugin list
```

For Antigravity 2.0 or standalone IDE, place the extracted `wp-devkit` folder under `.agents/plugins/` in your target project, or under `~/.gemini/config/plugins/` for all projects. Review active components in Customizations. Do not nest it inside another plugin's directory.

Use one installation method per scope to avoid duplicate skill names. Local installation does not publish this package in Google's marketplace. Available commands and interfaces depend on your installed Antigravity version.

## Start a review

Start a new conversation in the target WordPress project. Mention a matching skill by name, for example:

```text
Use wp-devkit-security-review to review wp-content/plugins/example-plugin.
Keep the review read-only. Report the evidence, impact and untested areas.
```

Antigravity 2.0 and CLI can invoke a skill as `/wp-devkit-security-review`. Confirm discovery in your installed client before relying on it. The 41 Claude namespaced commands are not part of this native Google package.

## Update carefully

Inspect local changes before replacing an installed package. Use your client's supported plugin management to update or remove it. Start a new session and confirm skill discovery after an update.

No server, lifecycle hooks, credentials or WordPress runtime are bundled. Install project tools separately when your selected task requires them. Package checks establish file completeness, not model judgment or successful loading in your particular client.

See Google's official [plugin guide](https://www.antigravity.google/docs/plugins/) and [skill locations](https://www.antigravity.google/docs/skills) for setup and version-specific behavior.
