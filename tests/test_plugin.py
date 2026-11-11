"""Fast tests for the directory-plugin contract and its storage/error boundaries."""

import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path
import unittest
from unittest.mock import patch

try:
    import pytest
except ImportError:  # plain unittest discovery without the dev extra
    raise unittest.SkipTest("tests/test_plugin.py needs pytest: python3 -m pip install '.[dev]'")

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "storybook_plugin_under_test", ROOT / "__init__.py",
    submodule_search_locations=[str(ROOT)],
)
assert SPEC is not None and SPEC.loader is not None
plugin = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = plugin
SPEC.loader.exec_module(plugin)
TOOL_NAMES = {"storybook_new", "storybook_validate", "storybook_build"}


class FakeContext:
    def __init__(self):
        self.tools = {}
        self.commands = {}
        self.command_meta = {}

    def register_tool(self, name, toolset, schema, handler, **kwargs):
        assert name not in self.tools
        self.tools[name] = {"toolset": toolset, "schema": schema, "handler": handler, **kwargs}

    def register_command(self, name, handler, description="", args_hint="", **kwargs):
        assert name not in self.commands
        self.commands[name] = handler
        self.command_meta[name] = {"description": description, "args_hint": args_hint}


@pytest.fixture
def registered(tmp_path, monkeypatch):
    data = tmp_path / "plugin-data"
    monkeypatch.setattr(plugin, "_data_root", lambda: data.resolve())
    ctx = FakeContext()
    plugin.register(ctx)
    return ctx, data


def call(ctx, name, args):
    result = ctx.tools[name]["handler"](args, task_id="test", future_context=True)
    assert isinstance(result, str)
    return json.loads(result)


def create(ctx, name="test-book"):
    result = call(ctx, "storybook_new", {"name": name, "pages": 1, "title": "Test book"})
    assert result["ok"], result
    return Path(result["story"])


def test_register_is_inert_and_matches_manifest(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("registration attempted I/O")

    monkeypatch.setattr(plugin, "_data_root", forbidden)
    with patch("subprocess.run", forbidden), patch("socket.socket", forbidden):
        ctx = FakeContext()
        plugin.register(ctx)
    assert set(ctx.tools) == TOOL_NAMES
    assert set(ctx.commands) == {"storybook"}
    manifest = (ROOT / "plugin.yaml").read_text(encoding="utf-8")
    declared = manifest.split("provides_tools:\n", 1)[1].split("provides_hooks:", 1)[0]
    assert {line.strip()[2:] for line in declared.splitlines() if line.strip()} == TOOL_NAMES
    assert "requires_env: []" in manifest
    for name, registration in ctx.tools.items():
        assert registration["toolset"] == "storybook"
        assert registration["schema"]["name"] == name
        assert registration["schema"]["parameters"]["required"] == ["name"]
    assert not any("visual" in name or "check" in name for name in ctx.tools)


def test_create_validate_build_end_to_end(registered):
    ctx, data = registered
    source = create(ctx)
    assert source == data / "stories" / "test-book" / "story.json"
    assert (source.parent / "research" / "ledger-template.json").is_file()
    validation = call(ctx, "storybook_validate", {"name": "test-book"})
    assert validation["ok"], validation
    assert json.loads(Path(validation["report"]).read_text()) == validation
    result = call(ctx, "storybook_build", {"name": "test-book"})
    assert result["ok"], result
    output = Path(result["html"])
    assert output == data / "dist" / "test-book" / "index.html"
    assert output.read_text().startswith("<!doctype html>")
    assert "Test book" in output.read_text()
    assert result["sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()


@pytest.mark.parametrize("tool", sorted(TOOL_NAMES))
@pytest.mark.parametrize("args", [None, [], {}, {"name": "../outside"}, {"name": "/absolute"}, {"name": "a/b"}, {"name": 4}])
def test_every_tool_rejects_bad_arguments(registered, tool, args):
    ctx, data = registered
    result = call(ctx, tool, args)
    assert result["ok"] is False
    assert result["error"]
    assert not data.exists()


@pytest.mark.parametrize("pages", [0, -1, 101, True, "3", 1.5])
def test_new_rejects_bad_page_counts(registered, pages):
    ctx, data = registered
    assert not call(ctx, "storybook_new", {"name": "test-book", "pages": pages})["ok"]
    assert not data.exists()


@pytest.mark.parametrize("title", [1, "", "   ", []])
def test_new_rejects_bad_titles(registered, title):
    ctx, _ = registered
    assert not call(ctx, "storybook_new", {"name": "test-book", "title": title})["ok"]


def test_new_does_not_overwrite(registered):
    ctx, _ = registered
    source = create(ctx)
    before = source.read_bytes()
    result = call(ctx, "storybook_new", {"name": "test-book"})
    assert not result["ok"]
    assert result["error_type"] == "FileExistsError"
    assert source.read_bytes() == before


@pytest.mark.parametrize("tool", ["storybook_validate", "storybook_build"])
@pytest.mark.parametrize("contents", [None, "{broken", "[]", "{}"])
def test_read_and_validation_errors_are_json(registered, tool, contents):
    ctx, data = registered
    if contents is not None:
        source = data / "stories" / "test-book" / "story.json"
        source.parent.mkdir(parents=True)
        source.write_text(contents)
    result = call(ctx, tool, {"name": "test-book"})
    assert not result["ok"]
    assert result["error"]
    assert not (data / "dist").exists()


@pytest.mark.parametrize("tool", sorted(TOOL_NAMES))
def test_every_tool_handles_storage_failure(registered, monkeypatch, tool):
    ctx, _ = registered
    def fail():
        raise PermissionError("storage unavailable")
    monkeypatch.setattr(plugin, "_data_root", fail)
    result = call(ctx, tool, {"name": "test-book"})
    assert not result["ok"]
    assert result["error_type"] == "PermissionError"


@pytest.mark.parametrize("tool", sorted(TOOL_NAMES))
def test_every_tool_handles_internal_failure(registered, monkeypatch, tool):
    ctx, _ = registered
    create(ctx)
    def fail(*args, **kwargs):
        raise RuntimeError("operation failed")
    if tool == "storybook_new":
        monkeypatch.setattr(plugin.new_story, "create_story", fail)
    else:
        monkeypatch.setattr(plugin.validate, "validate", fail)
    result = call(ctx, tool, {"name": "another-book" if tool == "storybook_new" else "test-book"})
    assert not result["ok"]
    assert result["error_type"] == "RuntimeError"


@pytest.mark.parametrize("tool", ["storybook_validate", "storybook_build"])
def test_strict_warnings_and_boolean_validation(registered, monkeypatch, tool):
    ctx, _ = registered
    create(ctx)
    monkeypatch.setattr(plugin.validate, "validate", lambda story: ([], ["test warning"]))
    result = call(ctx, tool, {"name": "test-book"})
    assert not result["ok"]
    assert result["warnings"] == ["test warning"]
    assert call(ctx, tool, {"name": "test-book", "strict": False})["ok"]
    assert not call(ctx, tool, {"name": "test-book", "strict": "false"})["ok"]


def test_failed_rebuild_leaves_previous_html_untouched(registered):
    ctx, _ = registered
    source = create(ctx)
    first = call(ctx, "storybook_build", {"name": "test-book"})
    output = Path(first["html"])
    before = output.read_bytes()
    source.write_text("{}")
    assert not call(ctx, "storybook_build", {"name": "test-book"})["ok"]
    assert output.read_bytes() == before


def test_build_render_failure_is_json(registered, monkeypatch):
    ctx, data = registered
    create(ctx)
    def fail(story):
        raise RuntimeError("render failed")
    monkeypatch.setattr(plugin.build, "render", fail)
    assert not call(ctx, "storybook_build", {"name": "test-book"})["ok"]
    assert not (data / "dist").exists()


@pytest.mark.parametrize("tool", ["storybook_validate", "storybook_build"])
def test_output_write_failure_is_json(registered, monkeypatch, tool):
    ctx, _ = registered
    create(ctx)
    with patch.object(Path, "write_text", side_effect=PermissionError("read only")):
        result = call(ctx, tool, {"name": "test-book"})
    assert not result["ok"]
    assert result["error_type"] == "PermissionError"


@pytest.mark.parametrize("tool", sorted(TOOL_NAMES))
def test_symlink_escape_is_rejected(registered, tmp_path, tool):
    ctx, data = registered
    outside = tmp_path / "outside"
    outside.mkdir()
    data.mkdir()
    (data / "stories").symlink_to(outside, target_is_directory=True)
    result = call(ctx, tool, {"name": "test-book"})
    assert not result["ok"]
    assert "escapes" in result["error"]
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("tool, folder, filename", [
    ("storybook_validate", "reports", "validation.json"),
    ("storybook_build", "dist", "index.html"),
])
def test_output_file_symlink_escape_is_rejected(registered, tmp_path, tool, folder, filename):
    ctx, data = registered
    create(ctx)
    outside = tmp_path / "outside.txt"
    outside.write_text("untouched")
    target = data / folder / "test-book" / filename
    target.parent.mkdir(parents=True)
    target.symlink_to(outside)
    result = call(ctx, tool, {"name": "test-book"})
    assert not result["ok"]
    assert outside.read_text() == "untouched"


def test_storage_helper_is_profile_scoped_and_not_cached(tmp_path):
    storage = types.ModuleType("plugins.plugin_storage")
    calls = []
    def plugin_data_dir(name):
        calls.append(name)
        return tmp_path / str(len(calls))
    setattr(storage, "plugin_data_dir", plugin_data_dir)
    with patch.dict(sys.modules, {"plugins": types.ModuleType("plugins"), "plugins.plugin_storage": storage}):
        assert plugin._data_root() == tmp_path / "1"
        assert plugin._data_root() == tmp_path / "2"
    assert calls == [plugin.PLUGIN_NAME, plugin.PLUGIN_NAME]


def test_slash_command_end_to_end(registered):
    ctx, _ = registered
    command = ctx.commands["storybook"]
    assert command("").startswith("/storybook - ") and "Usage:" in command("")
    created = command('new command-book "A quoted title"')
    assert created.startswith("Created story command-book")
    assert command("validate command-book").startswith("Valid: command-book")
    built = command("build command-book --strict")
    assert built.startswith("Built: command-book")
    html = Path(next(line for line in built.splitlines() if line.startswith("HTML: "))[len("HTML: "):])
    assert "A quoted title" in html.read_text()
    assert any(line.startswith("SHA-256: ") for line in built.splitlines())


@pytest.mark.parametrize("raw", ['new "unterminated', "new", "unknown book", "build book --out outside", "validate ../outside"])
def test_slash_command_error_paths(registered, raw):
    ctx, _ = registered
    reply = ctx.commands["storybook"](raw, task_id="t")
    assert isinstance(reply, str)
    assert reply.startswith(("storybook error:", "storybook ")) and not reply.startswith(("Created", "Valid", "Built"))


def test_error_envelope_names_the_tool_and_truncates(registered, monkeypatch):
    ctx, _ = registered
    long_message = "x" * 5000

    def fail():
        raise RuntimeError(long_message)

    monkeypatch.setattr(plugin, "_data_root", fail)
    for tool in sorted(TOOL_NAMES):
        result = call(ctx, tool, {"name": "test-book"})
        assert result["ok"] is False
        assert result["tool"] == tool
        assert result["error_type"] == "RuntimeError"
        assert len(result["error"]) <= plugin._MAX_ERROR_CHARS + 3


def test_command_is_registered_with_a_hint_and_returns_text(registered):
    ctx, data = registered
    assert ctx.command_meta["storybook"]["args_hint"]
    command = ctx.commands["storybook"]
    assert command("help") == plugin.HELP_TEXT
    failed = command("validate missing-book")
    assert failed.startswith("storybook validate failed:") and not failed.startswith("{")
    assert not data.exists()


def test_title_length_is_bounded(registered):
    ctx, data = registered
    result = call(ctx, "storybook_new", {"name": "test-book", "title": "t" * (plugin._MAX_TITLE_CHARS + 1)})
    assert result["ok"] is False and "title" in result["error"]
    assert not data.exists()


def test_register_describes_every_tool(registered):
    ctx, _ = registered
    for registration in ctx.tools.values():
        assert registration["description"] and registration["emoji"]


def test_plugin_entry_reads_no_credentials_or_global_state():
    source = (ROOT / "__init__.py").read_text(encoding="utf-8")
    for needle in ("environ", "getenv", ".env", "sys.path", "sys.argv", "chdir"):
        assert needle not in source, needle


def _load_visual_qa():
    spec = importlib.util.spec_from_file_location("visual_qa_under_test", ROOT / "tools" / "visual_qa.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_visual_qa_key_comes_from_secret_scope_and_a_miss_is_final(monkeypatch):
    visual_qa = _load_visual_qa()
    monkeypatch.setenv("OPENROUTER_API_KEY", "other-profile-value")
    agent = types.ModuleType("agent")
    scope = types.ModuleType("agent.secret_scope")
    scope.get_secret = lambda name, default=None: None
    agent.secret_scope = scope
    with patch.dict(sys.modules, {"agent": agent, "agent.secret_scope": scope}):
        assert visual_qa._api_key() is None
        scope.get_secret = lambda name, default=None: " scoped-value "
        assert visual_qa._api_key() == "scoped-value"
    with patch.dict(sys.modules, {"agent.secret_scope": None}):
        assert visual_qa._api_key() == "other-profile-value"
    monkeypatch.delenv("OPENROUTER_API_KEY")
    with patch.dict(sys.modules, {"agent.secret_scope": None}):
        assert visual_qa._api_key() is None


# --- /help text, README and visuals (docs pass) ------------------------------

import xml.etree.ElementTree as ET  # noqa: E402


def _readme():
    return (ROOT / "README.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("word", ["", "help", "HELP", "-h", "--help", "?"])
def test_help_words_all_print_the_help_text(registered, word):
    ctx, _ = registered
    assert ctx.commands["storybook"](word) == plugin.HELP_TEXT


def test_help_text_covers_every_action_and_tool():
    for needle in ["Usage:", "Examples:", "Notes:", "/storybook new", "/storybook validate", "/storybook build",
                   "/storybook help", *TOOL_NAMES]:
        assert needle in plugin.HELP_TEXT, needle
    assert max(len(line) for line in plugin.HELP_TEXT.splitlines()) <= 90


def test_bad_commands_point_to_help_without_repeating_it(registered):
    ctx, _ = registered
    for raw in ["new", "frobnicate book", "build book --out outside"]:
        reply = ctx.commands["storybook"](raw)
        assert reply.startswith("storybook error:") and "Run /storybook help for usage." in reply
        assert "Examples:" not in reply


def test_registered_hint_lists_the_actions(registered):
    ctx, _ = registered
    hint = ctx.command_meta["storybook"]["args_hint"]
    for needle in ["new", "validate", "build", "help"]:
        assert needle in hint


def test_readme_shows_the_exact_help_text():
    assert "```text\n" + plugin.HELP_TEXT + "\n```" in _readme()


def test_readme_troubleshooting_quotes_real_messages():
    source = (ROOT / "__init__.py").read_text(encoding="utf-8")
    for message in ["name must be 1-64 lowercase letters, numbers or hyphens", "Story validation failed; nothing built",
                    "Run /storybook help for usage."]:
        assert message in _readme() and message in source, message


def test_readme_visuals_exist_parse_and_stay_self_contained():
    readme = _readme()
    for name in ["banner.svg", "flow.svg"]:
        assert f"docs/assets/{name})" in readme
        path = ROOT / "docs" / "assets" / name
        root = ET.parse(path).getroot()
        assert root.tag.endswith("svg")
        assert root.find("{http://www.w3.org/2000/svg}title") is not None
        body = path.read_text(encoding="utf-8")
        assert "<script" not in body and "href=" not in body and "@import" not in body
        assert body.count("http") == body.count("http://www.w3.org/2000/svg")
