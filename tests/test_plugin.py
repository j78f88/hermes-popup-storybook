"""Fast tests for the directory-plugin contract and its storage/error boundaries."""

import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest

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

    def register_tool(self, name, toolset, schema, handler):
        assert name not in self.tools
        self.tools[name] = {"toolset": toolset, "schema": schema, "handler": handler}

    def register_command(self, name, handler, description=""):
        assert name not in self.commands
        self.commands[name] = handler


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
    assert "usage" in json.loads(command(""))
    assert json.loads(command('new command-book "A quoted title"'))["ok"]
    assert json.loads(command("validate command-book"))["ok"]
    result = json.loads(command("build command-book --strict"))
    assert result["ok"]
    assert "A quoted title" in Path(result["html"]).read_text()


@pytest.mark.parametrize("raw", ['new "unterminated', "new", "unknown book", "build book --out outside", "validate ../outside"])
def test_slash_command_error_paths(registered, raw):
    ctx, _ = registered
    assert not json.loads(ctx.commands["storybook"](raw))["ok"]
