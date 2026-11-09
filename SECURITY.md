# Security policy

## Supported release

Security fixes target the 1.0.x release line. Do not put sensitive details in a
public issue. Report a suspected vulnerability privately through this repository's
GitHub Security Advisories page when private reporting is available. If it is not,
open a minimal issue asking for a private contact without including payloads,
credentials, private stories or screenshots.

## Plugin boundaries

The registered tools are storybook_new, storybook_validate and storybook_build.
The /storybook command calls only these offline handlers. Registration does not
create files, read credentials, launch subprocesses or access the network.

Plugin calls use Hermes' profile-scoped plugin_data_dir("hermes-popup-storybook"):

- stories/<name>/ contains story JSON, planning templates and research ledgers.
- reports/<name>/validation.json holds the latest validation report.
- dist/<name>/index.html holds the latest validated build.

Names must be lowercase slugs, not paths. Resolved input and output paths must
stay under the plugin data root, including existing symlink targets. There is no
fallback to the working directory when Hermes storage is unavailable. Existing
story folders are never overwritten by creation. A build replaces the HTML for
that story only after validation passes; a failed rebuild leaves any previous
HTML untouched. Strict validation (warnings fail) is the default.

These checks are not an OS sandbox and do not defend against another local
process replacing paths during a call. Keep plugin data writable only by trusted
local users. The CLI scripts retain their explicit filesystem path arguments;
plugin confinement does not apply to standalone CLI use.

## Optional utilities are not plugin tools

The manifest discloses subprocesses used by the optional browser, build-and-check
and Git release-check scripts. Browser QA needs the qa extra and installed
Playwright browsers. No registered handler imports those helpers.

The separate tools/visual_qa.py CLI is deliberately not registered or invoked by
/storybook. It reads OPENROUTER_API_KEY through Hermes secret scope, or from its
process environment only when Hermes is not importable, and sends
screenshots and briefs to OpenRouter, or a configured OPENROUTER_URL, potentially
incurring charges. Use it only explicitly, with reviewed material and a trusted
endpoint. Never supply sensitive screenshots without permission. The default
plugin needs no key, stores no credentials and has no requires_env entries.

## Before sharing a book

The validator catches known secret and privacy patterns, not every disclosure
or unsupported factual claim. Review sources, prose, embedded images, rendered
HTML and screenshots before sharing. Validation is not HTML sandboxing or a
complete content-security audit. There is no automatic publishing or telemetry.
