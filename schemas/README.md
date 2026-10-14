# Bundled schemas

Copies of the Frontier JSON Schemas (draft 2020-12), published at
`https://dimensionlab.org/schemas/<name>.schema.json` and in the `frontier-format`
repository under `spec/schemas/`. The copies exist so the extension works offline and before
the URLs are live; `tests/test_extension.py` fails when a copy differs from the source.
Licence: CC-BY-4.0, like the rest of the specification.

| File | Validates | Files |
|------|-----------|-------|
| `frontier-config.schema.json` | the settings registry | `frontier.toml`, `~/.frontier/config.toml`, `/etc/frontier/config.toml` |
| `frontier-train-config.schema.json` | `frontier_train` configs (`task: transient` selects the transient branch) | `*.frontier.yaml`, `*.train.yaml`, `frontier-train/configs/*.yaml` |
| `runspec.schema.json` | `frontier.run/v1` RunSpecs | `*.runspec.yaml`, `runspec.yaml`, `*.runspec.json` |
| `jobspec.schema.json` | `frontier-cloud` JobSpecs | `*.jobspec.yaml`, `jobspec.yaml` |
| `recipe.schema.json` | `frontier_prep` recipes, each step's `params` tied to its `op` | `*.recipe.json` |
| `pipeline-v1.schema.json` | canvas / ingest pipelines | `pipeline.json`, `*.pipeline.json` |
| `hub-entry.schema.json` | hub catalog entries | `frontier_hub/catalog/<domain>/<id>.yaml`, `*.hub.yaml` |
| `benchmark-spec.schema.json` | `frontier_eval` benchmark specs | `frontier_eval/benchmarks/*.yaml`, `*.benchmark.yaml` |
| `plugin-manifest.schema.json` | plugin manifests | `plugin.toml` |

Refresh from a Frontier checkout with `pnpm nx run frontier-zed:sync-schemas`.
