// SPDX-License-Identifier: Apache-2.0
//! Frontier for Zed.
//!
//! The only part of this extension that needs Rust is the context server entry: Zed asks the
//! extension how to start the MCP server declared as `[context_servers.frontier]` in
//! `extension.toml`. Everything else (snippets, icon theme, bundled schemas, skills) is
//! plain configuration next to this crate.
//!
//! The server itself is `python -m frontier_agent mcp` from the `frontier-agent` Python
//! package (Apache-2.0, part of the Frontier SDK). Nothing is vendored here: the user's
//! environment provides the interpreter, and the settings below say which one.

use std::collections::HashMap;

use serde::Deserialize;
use zed_extension_api::{
    self as zed, Command, ContextServerConfiguration, ContextServerId, Project, Result,
    settings::ContextServerSettings,
};

/// Id of the context server as declared in `extension.toml`.
const SERVER_ID: &str = "frontier";

/// Interpreter used when neither `context_servers.frontier.settings.python` nor
/// `context_servers.frontier.command.path` is set. Resolved on the user's PATH by Zed.
const DEFAULT_PYTHON: &str = "python3";

/// User settings under `context_servers.frontier.settings` in Zed's `settings.json`.
/// All fields are optional; `configuration/settings_schema.json` is the schema Zed shows.
#[derive(Debug, Default, Deserialize)]
#[serde(default)]
struct FrontierSettings {
    /// Interpreter with `frontier-agent` installed (for example `/path/to/.venv/bin/python`).
    python: Option<String>,
    /// Directory where dataset names resolve (`--datasets-dir`).
    datasets_dir: Option<String>,
    /// Session record file the server appends every call to (`--record`).
    record: Option<String>,
    /// Approval mode (`--approver`): `none` (default, writes refused), `ui` or `auto`.
    approver: Option<String>,
    /// Extra arguments appended after `mcp`.
    extra_args: Vec<String>,
    /// Extra environment variables (`FRONTIER_DATASETS_DIR`, `FRONTIER_POLICY__AI_*`, ...).
    env: HashMap<String, String>,
}

/// The command line for the server, before Zed resolves the interpreter on PATH.
fn build_command(settings: &ContextServerSettings) -> Result<Command> {
    let user: FrontierSettings = match &settings.settings {
        Some(value) => serde::Deserialize::deserialize(value.clone())
            .map_err(|e| format!("context_servers.frontier.settings: {e}"))?,
        None => FrontierSettings::default(),
    };
    let command_override = settings.command.as_ref();

    let command = command_override
        .and_then(|c| c.path.clone())
        .or_else(|| user.python.clone())
        .unwrap_or_else(|| DEFAULT_PYTHON.to_string());

    let args = match command_override.and_then(|c| c.arguments.clone()) {
        // An explicit `command.arguments` replaces the whole argument list.
        Some(arguments) => arguments,
        None => {
            let mut args = vec![
                "-m".to_string(),
                "frontier_agent".to_string(),
                "mcp".to_string(),
            ];
            if let Some(dir) = &user.datasets_dir {
                args.push("--datasets-dir".to_string());
                args.push(dir.clone());
            }
            if let Some(record) = &user.record {
                args.push("--record".to_string());
                args.push(record.clone());
            }
            if let Some(approver) = &user.approver {
                match approver.as_str() {
                    "none" | "ui" | "auto" => {}
                    other => {
                        return Err(format!(
                            "context_servers.frontier.settings.approver: expected none, ui or auto, got {other:?}"
                        ));
                    }
                }
                args.push("--approver".to_string());
                args.push(approver.clone());
            }
            args.extend(user.extra_args.iter().cloned());
            args
        }
    };

    let mut env: Vec<(String, String)> = Vec::new();
    for (k, v) in &user.env {
        env.push((k.clone(), v.clone()));
    }
    if let Some(extra) = command_override.and_then(|c| c.env.clone()) {
        for (k, v) in extra {
            env.push((k, v));
        }
    }

    Ok(Command { command, args, env })
}

struct FrontierExtension;

impl zed::Extension for FrontierExtension {
    fn new() -> Self {
        Self
    }

    fn context_server_command(
        &mut self,
        context_server_id: &ContextServerId,
        project: &Project,
    ) -> Result<Command> {
        if context_server_id.as_ref() != SERVER_ID {
            return Err(format!(
                "unknown context server {}",
                context_server_id.as_ref()
            ));
        }
        let settings = ContextServerSettings::for_project(SERVER_ID, project)?;
        build_command(&settings)
    }

    fn context_server_configuration(
        &mut self,
        context_server_id: &ContextServerId,
        _project: &Project,
    ) -> Result<Option<ContextServerConfiguration>> {
        if context_server_id.as_ref() != SERVER_ID {
            return Ok(None);
        }
        Ok(Some(ContextServerConfiguration {
            installation_instructions: include_str!(
                "../configuration/installation_instructions.md"
            )
            .to_string(),
            default_settings: include_str!("../configuration/default_settings.jsonc").to_string(),
            settings_schema: include_str!("../configuration/settings_schema.json").to_string(),
        }))
    }
}

zed::register_extension!(FrontierExtension);
