# SPDX-License-Identifier: Apache-2.0
"""Checks for the Frontier Zed extension that need no Zed.

* `extension.toml` has the shape Zed's manifest loader (`ExtensionManifest`, schema
  version 1) expects, and every path it references exists.
* The bundled schemas are valid JSON Schema 2020-12 and identical to the monorepo's
  published copies when the test runs inside the monorepo.
* The settings snippets reference bundled schemas only, with the patterns the two language
  servers expect.
* Every snippet renders to a document that validates against its schema.
* The context server command is `python -m frontier_agent mcp` and, when the package is
  importable, it starts and answers `--help`.

Run: `uv run --no-sync pytest tools/frontier-zed/tests -q` (needs jsonschema and PyYAML,
both in the workspace environment). Set FRONTIER_ZED_BUILD=1 to also build the WASM crate.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import jsonschema
import pytest
import yaml

EXT = Path(__file__).resolve().parents[1]
MONOREPO_SCHEMAS = EXT.parents[1] / "docs" / "spec" / "schemas"
SCHEMA_DIR = EXT / "schemas"
SCHEMA_NAMES = {
    "benchmark-spec",
    "frontier-config",
    "frontier-train-config",
    "hub-entry",
    "jobspec",
    "pipeline-v1",
    "plugin-manifest",
    "recipe",
    "runspec",
}
SCHEMA_URL = "https://dimensionlab.org/schemas/"

# Zed manifest keys (crates/extension/src/extension_manifest.rs, schema version 1).
MANIFEST_KEYS = {
    "id",
    "name",
    "version",
    "schema_version",
    "description",
    "repository",
    "authors",
    "lib",
    "themes",
    "icon_themes",
    "languages",
    "grammars",
    "language_servers",
    "context_servers",
    "slash_commands",
    "snippets",
    "capabilities",
    "debug_adapters",
    "debug_locators",
    "language_model_providers",
}


def load_manifest() -> dict:
    return tomllib.loads((EXT / "extension.toml").read_text(encoding="utf-8"))


def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------------------ manifest


def test_manifest_shape():
    m = load_manifest()
    unknown = set(m) - MANIFEST_KEYS
    assert not unknown, f"keys Zed's manifest loader does not know: {sorted(unknown)}"
    assert m["schema_version"] == 1
    assert re.fullmatch(r"[a-z][a-z0-9-]*", m["id"]), m["id"]
    assert re.fullmatch(r"\d+\.\d+\.\d+", m["version"]), m["version"]
    assert m["name"] and m["description"] and m["repository"].startswith("https://")
    assert m["authors"]
    # Zed removed slash commands and deprecated agent-server extensions; we ship neither.
    assert "slash_commands" not in m
    assert "agent_servers" not in m


def test_manifest_paths_exist():
    m = load_manifest()
    for rel in m["snippets"] + m["icon_themes"]:
        assert (EXT / rel).is_file(), rel
    # Snippet files are matched to languages by file name.
    assert {Path(p).name for p in m["snippets"]} == {"json.json", "yaml.json", "toml.json"}


def test_no_custom_languages():
    """Frontier files must stay on Zed's JSON/YAML languages: a custom language would detach
    them from json-language-server / yaml-language-server and lose the schema diagnostics."""
    m = load_manifest()
    assert "languages" not in m and "grammars" not in m
    assert not (EXT / "languages").exists()


def test_version_matches_cargo():
    m = load_manifest()
    cargo = tomllib.loads((EXT / "Cargo.toml").read_text(encoding="utf-8"))
    assert cargo["package"]["version"] == m["version"]
    assert cargo["lib"]["crate-type"] == ["cdylib"]
    assert cargo["package"]["license"] == "Apache-2.0"
    assert "workspace" in cargo, "the crate must not join the monorepo workspace"
    assert re.fullmatch(r"\d+\.\d+\.\d+", cargo["dependencies"]["zed_extension_api"])


# ------------------------------------------------------------------------- context server


def test_context_server_entry():
    m = load_manifest()
    assert list(m["context_servers"]) == ["frontier"]
    lib = (EXT / "src" / "lib.rs").read_text(encoding="utf-8")
    assert 'const SERVER_ID: &str = "frontier";' in lib
    assert re.search(
        r'"-m"\.to_string\(\),\s*"frontier_agent"\.to_string\(\),\s*"mcp"\.to_string\(\)', lib
    )
    assert "fn context_server_command" in lib and "fn context_server_configuration" in lib
    assert "register_extension!(FrontierExtension)" in lib
    assert lib.startswith("// SPDX-License-Identifier: Apache-2.0")


def _strip_jsonc(text: str) -> str:
    return re.sub(r"^\s*//.*$", "", text, flags=re.M)


def test_context_server_default_settings_validate():
    schema = json.loads((EXT / "configuration" / "settings_schema.json").read_text("utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    raw = (EXT / "configuration" / "default_settings.jsonc").read_text("utf-8")
    defaults = json.loads(_strip_jsonc(raw))
    jsonschema.validate(defaults, schema)
    assert defaults["approver"] == "none", "Zed has no approval handler; writes must stay refused"
    instructions = (EXT / "configuration" / "installation_instructions.md").read_text("utf-8")
    assert "python -m frontier_agent mcp" in instructions


def test_context_server_command_runs():
    """`python -m frontier_agent mcp --help` with the interpreter running the tests."""
    try:
        import frontier_agent  # noqa: F401
    except ImportError:
        pytest.skip("frontier-agent is not installed in this interpreter")
    proc = subprocess.run(
        [sys.executable, "-m", "frontier_agent", "mcp", "--help"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    for flag in ("--approver", "--record", "--datasets-dir"):
        assert flag in proc.stdout, f"{flag} missing: the extension passes it"


# -------------------------------------------------------------------------------- schemas


def test_bundled_schemas_valid_and_named():
    found = {p.name.removesuffix(".schema.json") for p in SCHEMA_DIR.glob("*.schema.json")}
    assert found == SCHEMA_NAMES
    for name in SCHEMA_NAMES:
        schema = load_schema(name)
        jsonschema.Draft202012Validator.check_schema(schema)
        assert schema["$id"] == f"{SCHEMA_URL}{name}.schema.json"


@pytest.mark.skipif(not MONOREPO_SCHEMAS.is_dir(), reason="published schemas not alongside")
def test_bundled_schemas_match_published():
    for name in SCHEMA_NAMES:
        ours = (SCHEMA_DIR / f"{name}.schema.json").read_bytes()
        theirs = (MONOREPO_SCHEMAS / f"{name}.schema.json").read_bytes()
        assert ours == theirs, f"{name}: stale copy, run `pnpm nx run frontier-zed:sync-schemas`"


# ------------------------------------------------------------------------------- settings


@pytest.mark.parametrize("file", ["zed-settings.json", "zed-settings.local.json"])
def test_settings_snippets(file: str):
    s = json.loads((EXT / "settings" / file).read_text("utf-8"))
    lsp = s["lsp"]
    json_entries = lsp["json-language-server"]["settings"]["json"]["schemas"]
    yaml_entries = lsp["yaml-language-server"]["settings"]["yaml"]["schemas"]
    assert json_entries and yaml_entries

    def check_ref(url: str) -> None:
        if url.startswith(SCHEMA_URL):
            name = url[len(SCHEMA_URL) :]
        else:
            assert url.startswith("./tools/frontier-zed/schemas/"), url
            name = url.rsplit("/", 1)[1]
        assert (SCHEMA_DIR / name).is_file(), url

    for entry in json_entries:
        assert entry["fileMatch"], entry
        check_ref(entry["url"])
    for url, patterns in yaml_entries.items():
        assert patterns, url
        check_ref(url)
    referenced = {e["url"].rsplit("/", 1)[1] for e in json_entries} | {
        u.rsplit("/", 1)[1] for u in yaml_entries
    }
    # TOML (frontier.toml, plugin.toml) goes through the TOML extension's language server
    # and is not wired here; every JSON/YAML schema must be.
    wired = SCHEMA_NAMES - {"frontier-config", "plugin-manifest"}
    assert referenced == {f"{n}.schema.json" for n in wired}


# ------------------------------------------------------------------------------- snippets

TABSTOP = re.compile(
    r"\$\{(\d+)\|([^|]*)\|\}"  # ${1|a,b|} choice
    r"|\$\{(\d+):((?:[^{}]|\{[^{}]*\})*)\}"  # ${1:default}, one level of nesting
    r"|\$\{(\d+)\}|\$(\d+)"  # ${1}, $1
)


def render(body: list[str]) -> str:
    """Resolve tabstops the way an editor would on Tab-through: choices take the first
    option, placeholders their default text, bare stops become empty."""
    text = "\n".join(body)

    def sub(m: re.Match[str]) -> str:
        if m.group(2) is not None:
            return m.group(2).split(",")[0]
        if m.group(4) is not None:
            return render([m.group(4)])
        return ""

    for _ in range(4):  # nested placeholders
        new = TABSTOP.sub(sub, text)
        if new == text:
            break
        text = new
    return text.replace("\\$", "$")


SNIPPET_SCHEMA = {
    "json.json": {
        "frontier-recipe": "recipe",
        "frontier-pipeline": "pipeline-v1",
        "frontier-runspec": "runspec",
    },
    "yaml.json": {
        "frontier-train": "frontier-train-config",
        "frontier-train-transient": "frontier-train-config",
        "frontier-runspec": "runspec",
        "frontier-runspec-pipeline": "runspec",
        "frontier-jobspec": "jobspec",
        "frontier-hub-entry": "hub-entry",
        "frontier-benchmark": "benchmark-spec",
    },
    "toml.json": {
        "frontier-toml": "frontier-config",
        "frontier-plugin": "plugin-manifest",
    },
}


def load_snippets(file: str) -> dict:
    return json.loads((EXT / "snippets" / file).read_text("utf-8"))


@pytest.mark.parametrize("file", sorted(SNIPPET_SCHEMA))
def test_snippet_files_well_formed(file: str):
    snippets = load_snippets(file)
    assert snippets
    prefixes = []
    for name, s in snippets.items():
        assert isinstance(s["body"], list) and s["body"], name
        assert s["prefix"].startswith("frontier-"), name
        assert s["description"], name
        prefixes.append(s["prefix"])
    assert len(prefixes) == len(set(prefixes)), "duplicate prefixes"


@pytest.mark.parametrize(
    "file,prefix,schema_name",
    [(f, p, s) for f, m in SNIPPET_SCHEMA.items() for p, s in m.items()],
)
def test_snippet_renders_valid_document(file: str, prefix: str, schema_name: str):
    snippets = {s["prefix"]: s for s in load_snippets(file).values()}
    text = render(snippets[prefix]["body"])
    if file == "json.json":
        doc = json.loads(text)
    elif file == "yaml.json":
        doc = yaml.safe_load(text)
    else:
        doc = tomllib.loads(text)
    jsonschema.validate(doc, load_schema(schema_name))


def test_recipe_step_snippet_is_a_valid_step():
    snippets = {s["prefix"]: s for s in load_snippets("json.json").values()}
    step = json.loads(render(snippets["frontier-step"]["body"]))
    schema = load_schema("recipe")
    jsonschema.validate({"name": "x", "steps": [step]}, schema)


def test_site_profile_snippet_parses():
    snippets = {s["prefix"]: s for s in load_snippets("yaml.json").values()}
    doc = yaml.safe_load(render(snippets["frontier-site"]["body"]))
    assert doc["transport"]["kind"] == "ssh" and doc["runtime"] == "uv"


# --------------------------------------------------------------------------- skills, icons


def test_skills_follow_zed_format():
    skills = sorted((EXT / "skills").iterdir())
    assert [p.name for p in skills] == [
        "frontier-cleaning-recipe",
        "frontier-diagnose-dataset",
        "frontier-split-leakage",
    ]
    for d in skills:
        text = (d / "SKILL.md").read_text("utf-8")
        m = re.match(r"---\n(.*?)\n---\n", text, flags=re.S)
        assert m, d.name
        fm = yaml.safe_load(m.group(1))
        assert fm["name"] == d.name
        assert re.fullmatch(r"[a-z0-9-]{1,64}", fm["name"])
        assert 0 < len(fm["description"]) <= 1024
        assert "never invent" in text.lower() or "approval" in text.lower()


def test_icon_theme_paths_exist():
    m = load_manifest()
    for rel in m["icon_themes"]:
        theme = json.loads((EXT / rel).read_text("utf-8"))
        assert theme["$schema"] == "https://zed.dev/schema/icon_themes/v0.3.0.json"
        for t in theme["themes"]:
            icons = t["file_icons"]
            for key, icon in icons.items():
                path = EXT / icon["path"]
                assert path.is_file(), f"{key}: {icon['path']}"
                svg = path.read_text("utf-8")
                assert "currentColor" in svg and "#" not in svg, f"{key}: not theme-agnostic"
            for kind in ("directory_icons", "chevron_icons"):
                for p in t[kind].values():
                    assert (EXT / p).is_file(), p
            for table in ("file_stems", "file_suffixes"):
                for k, key in t[table].items():
                    assert key in icons, f"{table}[{k}] -> {key} has no file_icons entry"


# ----------------------------------------------------------------------------- wasm build


@pytest.mark.skipif(
    os.environ.get("FRONTIER_ZED_BUILD") != "1" or shutil.which("cargo") is None,
    reason="set FRONTIER_ZED_BUILD=1 with cargo and the wasm32-wasip2 target installed",
)
def test_wasm_build():
    manifest = str(EXT / "Cargo.toml")
    proc = subprocess.run(
        ["cargo", "build", "--release", "--target", "wasm32-wasip2", "--manifest-path", manifest],
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert proc.returncode == 0, proc.stderr[-4000:]
    # A `.cargo/config.toml` above the crate may move the target directory (the Frontier
    # monorepo uses dist/target), so ask cargo where it put the artifact.
    meta = subprocess.run(
        ["cargo", "metadata", "--format-version", "1", "--no-deps", "--manifest-path", manifest],
        capture_output=True,
        text=True,
        check=True,
    )
    target_dir = Path(json.loads(meta.stdout)["target_directory"])
    assert (target_dir / "wasm32-wasip2" / "release" / "frontier_zed.wasm").is_file()
