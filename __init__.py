"""Offline popup-storybook tools for Hermes directory and wheel installs."""

import functools
import hashlib
import json
import shlex
from pathlib import Path

from .engine import build, validate
from .tools import new_story

PLUGIN_NAME = "hermes-popup-storybook"
_MAX_ERROR_CHARS = 500
_MAX_TITLE_CHARS = 200
HELP_TEXT = """\
/storybook - build an offline pop-up storybook from one story file

Usage:
  /storybook new <name> ["Title"]         Create a starter story folder
  /storybook validate <name> [--strict]   Check the story and write a report
  /storybook build <name> [--strict]      Validate, then write one offline HTML file
  /storybook help                         Show this message

<name> is a lowercase slug, not a path. Validation is always strict.

Examples:
  /storybook new my-book "My book"
  /storybook validate my-book
  /storybook build my-book

Notes:
  Stories, reports and HTML stay in the plugin data folder. No network, no credentials.
  Edit the story file that "new" prints, then validate and build again.
  The same steps are available to the agent as storybook_new, storybook_validate
  and storybook_build."""
USAGE = HELP_TEXT  # name kept for callers that imported the old constant
HELP_WORDS = frozenset({"help", "-h", "--help", "?"})


def _data_root():
    # Resolve on every invocation: a long-lived process may switch profiles.
    # No cwd fallback: outside Hermes the caller must provide a storage adapter.
    from plugins.plugin_storage import plugin_data_dir

    return Path(plugin_data_dir(PLUGIN_NAME)).resolve()


def _path(root, *parts):
    path = root.joinpath(*parts).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Path escapes the plugin data directory")
    return path


def _name(args):
    if not isinstance(args, dict):
        raise ValueError("Tool arguments must be an object")
    name = args.get("name")
    if not isinstance(name, str) or len(name) > 64 or not new_story.NAME_PATTERN.fullmatch(name):
        raise ValueError("name must be 1-64 lowercase letters, numbers or hyphens, starting with a letter or number")
    return name


def _error_payload(tool, error):
    message = str(error) or type(error).__name__
    if len(message) > _MAX_ERROR_CHARS:
        message = message[:_MAX_ERROR_CHARS] + "..."
    return {"ok": False, "tool": tool, "error": message, "error_type": type(error).__name__}


def _json_handler(handler):
    """Return a JSON string for every call and never raise; errors name the tool."""

    @functools.wraps(handler)
    def wrapped(args=None, **kwargs):
        try:
            return json.dumps(handler(args, **kwargs), ensure_ascii=False)
        except Exception as error:  # noqa: BLE001 - tool contract: always return JSON
            return json.dumps(_error_payload(handler.__name__, error), ensure_ascii=False)

    return wrapped


@_json_handler
def storybook_new(args, **kwargs):
    """Create a scaffold using the same implementation as tools/new_story.py."""
    name = _name(args)
    pages = args.get("pages", 3)
    if isinstance(pages, bool) or not isinstance(pages, int) or not 1 <= pages <= 100:
        raise ValueError("pages must be an integer from 1 to 100")
    title = args.get("title")
    if title is not None and (not isinstance(title, str) or not title.strip() or len(title) > _MAX_TITLE_CHARS):
        raise ValueError(f"title must be a non-empty string of at most {_MAX_TITLE_CHARS} characters")
    root = _data_root()
    parent = _path(root, "stories")
    _path(root, "stories", name)
    story = new_story.create_story(name, parent, title=title, pages=pages)
    return {"ok": True, "name": name, "story": str(story), "pages": pages}


def _checked_story(args):
    name = _name(args)
    strict = args.get("strict", True)
    if not isinstance(strict, bool):
        raise ValueError("strict must be a boolean")
    root = _data_root()
    source = _path(root, "stories", name, "story.json")
    story = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(story, dict):
        raise ValueError("Story JSON must be an object")
    errors, warnings = validate.validate(story)
    valid = not errors and not (strict and warnings)
    result = {
        "ok": valid,
        "valid": valid,
        "name": name,
        "story": str(source),
        "strict": strict,
        "errors": errors,
        "warnings": warnings,
    }
    if not valid:
        result["error"] = "Story validation failed; nothing built"
    return root, story, result


@_json_handler
def storybook_validate(args, **kwargs):
    """Validate an existing plugin story and persist the report."""
    root, _, result = _checked_story(args)
    report = _path(root, "reports", result["name"], "validation.json")
    result["report"] = str(report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


@_json_handler
def storybook_build(args, **kwargs):
    """Validate and render offline HTML without invoking a shell or browser."""
    root, story, result = _checked_story(args)
    if not result["valid"]:
        return result
    output = _path(root, "dist", result["name"], "index.html")
    html = build.render(story)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    result.update({"html": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()})
    return result


def _command_text(action, payload):
    """Render a tool result as plain text for the slash command."""
    if not payload.get("ok"):
        lines = [f"storybook {action} failed: {payload.get('error') or 'story is not valid'}"]
        lines += [f"  error: {item}" for item in payload.get("errors", [])]
        lines += [f"  warning: {item}" for item in payload.get("warnings", [])]
        return "\n".join(lines)
    if action == "new":
        return f"Created story {payload['name']} ({payload['pages']} pages)\nStory: {payload['story']}"
    lines = [f"{'Built' if action == 'build' else 'Valid'}: {payload['name']}"]
    lines += [f"  warning: {item}" for item in payload.get("warnings", [])]
    if action == "validate":
        lines.append(f"Report: {payload['report']}")
    else:
        lines += [f"HTML: {payload['html']}", f"SHA-256: {payload['sha256']}"]
    return "\n".join(lines)


def storybook_command(raw_args="", **kwargs):
    """Dispatch /storybook locally as plain text. Input is tokenized, never shell-executed, and never raises."""
    try:
        parts = shlex.split(raw_args or "")
        if not parts or (len(parts) == 1 and parts[0].lower() in HELP_WORDS):
            return HELP_TEXT
        if len(parts) < 2:
            raise ValueError(f"incomplete command {parts[0]!r}. Run /storybook help for usage.")
        action, name, *rest = parts
        if action == "new":
            args = {"name": name}
            if rest:
                args["title"] = " ".join(rest)
            return _command_text(action, json.loads(storybook_new(args)))
        if action in {"validate", "build"} and rest in ([], ["--strict"]):
            handler = storybook_validate if action == "validate" else storybook_build
            return _command_text(action, json.loads(handler({"name": name, "strict": True})))
        raise ValueError(f"cannot run {action!r} with those arguments. Run /storybook help for usage.")
    except Exception as error:  # noqa: BLE001 - never crash the session
        return f"storybook error: {error}"


def _schema(name, description, extra):
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Story slug in plugin storage, not a filesystem path",
                    "pattern": "^[a-z0-9][a-z0-9-]*$",
                    "minLength": 1,
                    "maxLength": 64,
                },
                **extra,
            },
            "required": ["name"],
            "additionalProperties": False,
        },
    }


def register(ctx):
    """Register only offline, unauthenticated tools; perform no startup I/O."""
    ctx.register_tool(
        name="storybook_new",
        toolset="storybook",
        schema=_schema("storybook_new", "Create a private story scaffold under plugin data; refuses to overwrite existing stories.", {
            "title": {"type": "string", "minLength": 1, "maxLength": _MAX_TITLE_CHARS, "description": "Cover title; defaults to the story name"},
            "pages": {"type": "integer", "minimum": 1, "maximum": 100, "default": 3},
        }),
        handler=storybook_new,
        description="Create a private offline story scaffold",
        emoji="📖",
    )
    strict = {"strict": {"type": "boolean", "default": True, "description": "Treat validation warnings as failures"}}
    ctx.register_tool(
        name="storybook_validate",
        toolset="storybook",
        schema=_schema("storybook_validate", "Validate a plugin story's structure, sources and privacy patterns; save a JSON report.", strict),
        handler=storybook_validate,
        description="Validate an offline story and save a report",
        emoji="🔍",
    )
    ctx.register_tool(
        name="storybook_build",
        toolset="storybook",
        schema=_schema("storybook_build", "Validate a plugin story, then build one offline HTML book in plugin data; returns its path and SHA-256.", strict),
        handler=storybook_build,
        description="Build one offline HTML storybook",
        emoji="🛠️",
    )
    ctx.register_command(
        "storybook",
        storybook_command,
        description="Create, validate or build an offline pop-up storybook",
        args_hint="new|validate|build <name> | help",
    )
