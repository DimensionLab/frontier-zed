# Frontier for Zed

A [Zed](https://zed.dev) extension for [DimensionLab Frontier](https://dimensionlab.org),
the platform for training, understanding and deploying large physics models. It makes Zed
understand Frontier's files and puts Frontier's data tools in Zed's agent panel.

Licence: Apache-2.0 for everything in this repository. Nothing of Frontier itself is
vendored: the extension is configuration plus a small WebAssembly shim that launches a
program from your own Python environment, and the schemas are the public specification
(CC-BY-4.0).

| Piece                     | What you get                                                                                                                                                                                                                                                                                                         | Needs                                                                   |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| Schema associations       | Completion, hover and diagnostics for training configs, RunSpecs, JobSpecs, data-prep recipes, pipelines, hub entries and benchmark specs, through Zed's built-in `json-language-server` and `yaml-language-server`                                                                                                  | one settings block (below)                                              |
| Bundled schemas           | The nine Frontier JSON Schemas in `schemas/`, identical to `spec/schemas/` in the frontier-format repository                                                                                                                                                                                                         | nothing                                                                 |
| Snippets                  | `frontier-train`, `frontier-train-transient`, `frontier-runspec`, `frontier-runspec-pipeline`, `frontier-jobspec`, `frontier-hub-entry`, `frontier-benchmark`, `frontier-site` (YAML); `frontier-recipe`, `frontier-step`, `frontier-pipeline`, `frontier-runspec` (JSON); `frontier-toml`, `frontier-plugin` (TOML) | nothing; TOML snippets need the TOML extension                          |
| Context server `frontier` | Frontier's MCP server in the agent panel: `dataset.*`, `version.*`, `quality.*`, `judge.*`, `prep.*` tools and the `frontier://datasets`, `frontier://dataset/{name}/card`, `frontier://dataset/{name}/provenance`, `frontier://policy` resources                                                                    | a Python environment with Frontier's `frontier-agent` package installed |
| Skills                    | `frontier-diagnose-dataset`, `frontier-cleaning-recipe`, `frontier-split-leakage` for Zed's agent (the Pi package's prompts, in Zed's skill format)                                                                                                                                                                  | copy or symlink into `~/.agents/skills/`                                |
| Icon theme                | "Frontier Minimal": file icons for Frontier files, drawn with `currentColor`                                                                                                                                                                                                                                         | opt-in; see Icons                                                       |

Screenshots: `docs/screenshots/zed-schema-diagnostics.png` and
`docs/screenshots/zed-context-server.png` (placeholders until the first release is captured
in a real Zed; see Status).

## Install

**Dev extension (now).** In Zed run `zed: install dev extension` (or _Extensions_ →
_Install Dev Extension_) and pick this directory (`tools/frontier-zed` in a Frontier
checkout, or a clone of `DimensionLab/frontier-zed`). Zed compiles the Rust crate itself; it
needs `rustup` with the `wasm32-wasip2` target, which Zed adds when it is missing. To build
by hand:

```sh
rustup target add wasm32-wasip2
cargo build --release --target wasm32-wasip2 --manifest-path tools/frontier-zed/Cargo.toml
```

The crate is not a member of the Frontier workspace (it has its own `[workspace]` table),
so `cargo build --workspace` at the repository root never touches it. Inside the monorepo
the artifact lands in `dist/target/wasm32-wasip2/release/frontier_zed.wasm` (the root
`.cargo/config.toml` sets the target directory); in a standalone clone, in `target/`.

**Extension registry (later).** Once published, _Extensions_ → search "Frontier". The
registry submission is a pull request to `zed-industries/extensions` that adds this
repository as a git submodule and an entry in `extensions.toml`; it is not done yet.

## Schema diagnostics

Zed associates JSON Schemas with files through language-server settings, not through
extension manifests, so one settings block is needed. Copy
[`settings/zed-settings.json`](settings/zed-settings.json) into your user settings
(`zed: open settings`) or into a project's `.zed/settings.json`. It maps:

| Pattern                                                               | Schema                                              |
| --------------------------------------------------------------------- | --------------------------------------------------- |
| `*.frontier.yaml`, `*.train.yaml`, `**/frontier-train/configs/*.yaml` | `frontier-train-config`                             |
| `*.runspec.yaml`, `runspec.yaml`, `*.runspec.json`                    | `runspec`                                           |
| `*.jobspec.yaml`, `jobspec.yaml`, `*.jobspec.json`                    | `jobspec`                                           |
| `*.recipe.json`, `recipe.json`                                        | `recipe` (each step's `params` is tied to its `op`) |
| `pipeline.json`, `*.pipeline.json`                                    | `pipeline-v1`                                       |
| `*.hub.yaml`, `**/frontier_hub/catalog/*/*.yaml`                      | `hub-entry`                                         |
| `*.benchmark.yaml`, `**/frontier_eval/benchmarks/*.yaml`              | `benchmark-spec`                                    |

`settings/zed-settings.json` points at the published URLs
(`https://dimensionlab.org/schemas/<name>.schema.json`). Until those URLs are live, or when
you work offline, use [`settings/zed-settings.local.json`](settings/zed-settings.local.json),
which points at the bundled copies through `./tools/frontier-zed/schemas/...` (Zed resolves
`./` against the worktree root, so this form is for a Frontier checkout; elsewhere replace the
prefix with the absolute path of your clone, `~/` is expanded too).

Two per-file alternatives need no settings: a `"$schema": "<url or path>"` key at the top
of a JSON document, or a `# yaml-language-server: $schema=<url or path>` modeline as the
first line of a YAML document.

**TOML (`frontier.toml`, `plugin.toml`).** TOML is not built into Zed; install the TOML
extension (its language server is Tombi). Frontier validates these files itself
(`frontier config check`, `frontier plugin check`) and the schemas are bundled for whatever
association mechanism your TOML language server offers; the extension does not wire them.

**Site profiles** (`~/.frontier/sites/<name>.yaml`) have no published schema yet; the
`frontier-site` snippet gives the shape and `frontier sites` validates them.

## The `frontier` context server

Declared in `extension.toml` as `[context_servers.frontier]`; `src/lib.rs` tells Zed to run

```
<python> -m frontier_agent mcp [--datasets-dir D] [--record F] [--approver none|ui|auto] [extra args]
```

over stdio. `frontier_agent` is the `frontier-agent` package that ships with Frontier (it is
not on PyPI; a Frontier installation or checkout provides it, `uv sync` in a checkout gives
`.venv/bin/python`). `python` must be an interpreter that has it. Configure it in Zed's
`settings.json` (Zed also
shows these settings, with a schema, when you enable the server in the agent panel):

```json
{
  "context_servers": {
    "frontier": {
      "settings": {
        "python": "/path/to/frontier/.venv/bin/python",
        "datasets_dir": "/path/to/frontier/datasets",
        "approver": "none",
        "env": {}
      }
    }
  }
}
```

`command.path`, `command.arguments` and `command.env` under `context_servers.frontier`
override the interpreter, the whole argument list and the environment, as for any Zed
context server. Check the server from a terminal first:
`/path/to/.venv/bin/python -m frontier_agent mcp --help`.

What the agent sees: 15 fixed tools plus `plan`/`preview`/`run` for every data-prep op,
with the op's own parameter schema; the resources above as context. Tool names are the
server's (`dataset.describe`, `prep.fields.rename.plan`, ...).

**Approvals.** Keep `approver` at `none`. In that mode every operation that writes
(`<op>.run`, `version.revert`) is refused unless the site policy
(`policy.ai.autonomous_op_classes`) grants autonomy for the op class, because Zed has no
handler that turns `prep.request_approval` into a dialog whose answer the server can trust
(`ui` is for clients such as the Pi package that intercept the call; a model could otherwise
answer its own approval). Data-prep sessions with approvals in Zed are the job of the
Frontier ACP agent, `python -m frontier_agent acp`, specified in `spec/acp.md` of the
frontier-format repository and configured as an external agent in Zed (`agent_servers`),
not as a context server.

**Policy.** `policy.ai.data_leaves_site`, `allowed_providers` and the rest apply inside the
server; the judge backend the tools use is chosen there, not by the model Zed's panel runs.

The `frontier` CLI is not required by the extension. `frontier` on your PATH is what the
_Open in Zed_ story below assumes, and what `frontier prep` needs to run recipes.

## Skills (prompt templates)

Zed replaced its Rules Library with Skills (Zed 1.4). The three procedures the Pi package
ships as prompts are here as skills; install them by copying or symlinking each directory
under `skills/` into `~/.agents/skills/` (all projects) or `<project>/.agents/skills/`
(one project), then type `/frontier-diagnose-dataset` or `@frontier-cleaning-recipe` in
the agent panel, or let the agent pick them up from the catalog:

```sh
ln -s "$PWD/tools/frontier-zed/skills/"* ~/.agents/skills/
```

Extensions cannot ship skills yet, so this step is manual. A project `.rules` or
`AGENTS.md` is the place for site conventions (dataset directory, which judge backend is
allowed); Zed reads the first of `.rules`, `.cursorrules`, `.windsurfrules`, `.clinerules`,
`.github/copilot-instructions.md`, `AGENT.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`.

## Icons

`icon_themes/frontier.json` is the "Frontier Minimal" icon theme: file icons for
`frontier.toml`, `plugin.toml`, `*.recipe.json`, `pipeline.json`, `*.runspec.yaml`,
`*.frontier.yaml`, `*.hub.yaml`, drawn as 16 px strokes in `currentColor`, so they follow
any Zed theme. Zed has no API to add icons to the active theme: an icon theme is whole, and
only its stem/suffix tables merge with the default theme, so selecting it gives every
non-Frontier file the plain `file.svg` icon. It is therefore off unless you choose it
(`icon_theme: "Frontier Minimal"` in settings). The SVGs are also the source for the app's
own file-kind glyphs.

## Open in Zed

Frontier's app and TUI hand heavy editing to Zed through Zed's CLI (`zed`, installed from
Zed's _Install CLI_ command). The forms, from Zed's CLI reference:

| Action                                                        | Command Frontier runs or shows                                          |
| ------------------------------------------------------------- | ----------------------------------------------------------------------- |
| Open a file at a position                                     | `zed /abs/path/file.yaml:LINE:COL` (1-based; `:LINE` alone works)       |
| Open a run's artifact directory next to the current workspace | `zed --add /abs/path/runs/<id>`                                         |
| Compare two configs or recipe versions                        | `zed --diff /abs/old.yaml /abs/new.yaml` (repeatable for several pairs) |
| Wait for the editor to close (scripts, `$EDITOR`)             | `zed --wait /abs/path`                                                  |

On the desktop app the command is spawned directly; on the web app the server reports a
local path for the artifact (mounted share) and the UI shows the command to copy, because no
`zed://` URL form that opens a file at a line is documented. VS Code gets
`vscode://file/ABS/PATH:LINE:COL` for the same action.

## Layout

```
extension.toml           manifest (schema_version 1): snippets, icon theme, [context_servers.frontier]
Cargo.toml, src/lib.rs   the wasm32-wasip2 shim: context_server_command + context_server_configuration
configuration/           installation text, default settings and settings schema Zed shows for the server
schemas/                 bundled JSON Schemas (copies of the published spec/schemas/)
settings/                settings blocks for json-language-server and yaml-language-server
snippets/                json.json, yaml.json, toml.json (matched to languages by file name)
skills/                  three agent skills (SKILL.md)
icons/, icon_themes/     the opt-in icon theme
tests/                   pytest: manifest shape, schemas, settings, snippets validate, server command
```

## Develop

```sh
uv run --no-sync pytest tools/frontier-zed/tests -q            # or: pnpm nx run frontier-zed:test
FRONTIER_ZED_BUILD=1 uv run --no-sync pytest tools/frontier-zed/tests -q -k wasm
pnpm nx run frontier-zed:build                                  # cargo build for wasm32-wasip2
pnpm nx run frontier-zed:sync-schemas                           # refresh schemas/ from the monorepo's published schemas
```

The tests render every snippet (first choice, default placeholders) and validate the result
against its schema, so a schema change that breaks a snippet fails here.

Zed facts this extension relies on were checked on 2026-10-11 against zed.dev/docs,
`zed-industries/zed` (`crates/extension/src/extension_manifest.rs`) and crates.io
(`zed_extension_api` 0.7.0): manifest schema version 1; extensions compile to
`wasm32-wasip2`; context servers need a Rust crate (`context_server_command`,
`context_server_configuration`); snippets are listed in the manifest and matched by file
name; icon themes use schema v0.3.0 and only stems/suffixes merge with the default theme;
slash commands are removed and agent-server extensions deprecated in favour of the ACP
registry; the Rules Library became Skills in `~/.agents/skills/`; Zed plans to deprecate
context-server extensions in favour of the MCP registry (tracked in zed-industries/zed#59351),
which is why the server will also be published there.

## Status

- Not yet tried in a real Zed: the machine this was built on has no Zed installed. The
  manifest, the WASM build and the server command are covered by tests; the first run in
  Zed should confirm the dev-extension install, the diagnostics on a training config and the
  server in the agent panel, and capture the two screenshots.
- `https://dimensionlab.org/schemas/` is not serving the schemas yet; use the local settings
  block until it does.
- Zed extension registry and MCP registry submissions pending.
