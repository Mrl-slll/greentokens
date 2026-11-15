//! Bridge from the UI to the bundled Python agent (agent/gt_agent.py).
//! Only a fixed list of actions is accepted, every argument is validated here and again in
//! Python, and calls run one at a time. The first call sets up a private Python + Ray runtime
//! with the bundled uv, inside this app's own data folder.

use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::Mutex;
use tauri::path::BaseDirectory;
use tauri::{AppHandle, Manager};

const PYTHON_VERSION: &str = "3.12";
const RAY_REQUIREMENT: &str = "ray[default]==2.60.0";
const RUNTIME_MARKER: &str = "greentokens-runtime-ray-2.60.0";
const UV_RESOURCE: &str = if cfg!(windows) { "bin/uv.exe" } else { "bin/uv" };
const ACTIONS: &[&str] = &["check", "firewall", "host", "join", "stop", "status"];

static AGENT_LOCK: Mutex<()> = Mutex::new(());

struct Paths {
    uv: PathBuf,
    agent: PathBuf,
    data: PathBuf,
    env: PathBuf,
    python: PathBuf,
}

fn missing(_: tauri::Error) -> String {
    "Some app files are missing. Please reinstall GreenTokens Provider.".to_string()
}

fn paths(app: &AppHandle) -> Result<Paths, String> {
    let uv = app.path().resolve(UV_RESOURCE, BaseDirectory::Resource).map_err(missing)?;
    let agent = app.path().resolve("agent/gt_agent.py", BaseDirectory::Resource).map_err(missing)?;
    let data = app
        .path()
        .app_local_data_dir()
        .map_err(|_| "Can't find this app's data folder.".to_string())?;
    let env = data.join("runtime");
    let python = if cfg!(windows) { env.join("Scripts").join("python.exe") } else { env.join("bin").join("python3") };
    Ok(Paths { uv, agent, data, env, python })
}

fn command(program: &Path, p: &Paths) -> Command {
    let mut c = Command::new(program);
    c.env("UV_CACHE_DIR", p.data.join("uv-cache"));
    c.env("UV_PYTHON_INSTALL_DIR", p.data.join("python"));
    c.env("UV_PYTHON_PREFERENCE", "only-managed"); // same Python on every computer in a group
    c.env("UV_NO_CONFIG", "1");
    c.env("PYTHONUTF8", "1");
    c.stdin(Stdio::null());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        c.creation_flags(0x0800_0000); // CREATE_NO_WINDOW
    }
    c
}

fn run(mut c: Command, what: &str) -> Result<String, String> {
    let out = c.output().map_err(|_| format!("Could not start {what}."))?;
    if out.status.success() {
        return Ok(String::from_utf8_lossy(&out.stdout).into_owned());
    }
    let stderr = String::from_utf8_lossy(&out.stderr);
    let last: String = stderr
        .lines()
        .rev()
        .find(|l| !l.trim().is_empty())
        .unwrap_or("")
        .trim()
        .chars()
        .take(200)
        .collect();
    Err(format!("{what} failed. Check your internet connection and try again. {last}"))
}

fn ensure_runtime(p: &Paths) -> Result<(), String> {
    let marker = p.env.join(RUNTIME_MARKER);
    if marker.is_file() && p.python.is_file() {
        return Ok(());
    }
    std::fs::create_dir_all(&p.data).map_err(|_| "Can't write to this app's data folder.".to_string())?;
    if !p.python.is_file() {
        let mut c = command(&p.uv, p);
        c.args(["venv", "--quiet", "--python", PYTHON_VERSION]).arg(&p.env);
        run(c, "Setting up Python")?;
    }
    let mut c = command(&p.uv, p);
    c.args(["pip", "install", "--quiet", "--python"]).arg(&p.python).arg(RAY_REQUIREMENT);
    run(c, "Installing the computing runtime")?;
    std::fs::write(&marker, b"ok").map_err(|_| "Can't write to this app's data folder.".to_string())?;
    Ok(())
}

fn valid_code(code: &str) -> bool {
    code.len() <= 64
        && code.starts_with("GT1-")
        && code.chars().all(|c| c.is_ascii_alphanumeric() || c == '.' || c == '-')
}

#[tauri::command]
pub async fn agent(
    app: AppHandle,
    action: String,
    cpus: Option<u32>,
    code: Option<String>,
) -> Result<serde_json::Value, String> {
    if !ACTIONS.contains(&action.as_str()) {
        return Err("Unknown action.".to_string());
    }
    let cpus = cpus.unwrap_or(1);
    if !(1..=256).contains(&cpus) {
        return Err("Invalid processor limit.".to_string());
    }
    if let Some(c) = &code {
        if !valid_code(c) {
            return Err("That group code doesn't look right.".to_string());
        }
    }
    tauri::async_runtime::spawn_blocking(move || run_agent(&app, &action, cpus, code.as_deref()))
        .await
        .map_err(|_| "The request was interrupted.".to_string())?
}

fn run_agent(app: &AppHandle, action: &str, cpus: u32, code: Option<&str>) -> Result<serde_json::Value, String> {
    let _guard = AGENT_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let p = paths(app)?;
    if action == "stop" && !p.python.is_file() {
        return Ok(serde_json::json!({ "ok": true, "connected": false }));
    }
    ensure_runtime(&p)?;
    let mut c = command(&p.python, &p);
    c.arg(&p.agent).arg(action).arg("--cpus").arg(cpus.to_string());
    if let Some(code) = code {
        c.arg("--code").arg(code);
    }
    let stdout = run(c, "The GreenTokens agent")?;
    let line = stdout
        .lines()
        .rev()
        .find(|l| l.trim_start().starts_with('{'))
        .ok_or("The GreenTokens agent gave no answer.")?;
    serde_json::from_str(line).map_err(|_| "The GreenTokens agent gave an unreadable answer.".to_string())
}

/// Called when the window closes: never keep sharing after the app is gone.
pub fn stop_on_exit(app: &AppHandle) {
    let _guard = AGENT_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    if let Ok(p) = paths(app) {
        if p.python.is_file() {
            let mut c = command(&p.python, &p);
            c.arg(&p.agent).arg("stop");
            let _ = c.output();
        }
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn validates_codes() {
        assert!(super::valid_code("GT1-192.168.1.20-0123456789abcdef0123456789abcdef"));
        assert!(!super::valid_code("GT1-192.168.1.20-abc; calc"));
        assert!(!super::valid_code("hello"));
    }
}
