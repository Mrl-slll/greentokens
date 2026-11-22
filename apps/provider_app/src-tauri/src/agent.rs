//! Bridge from the UI to the bundled Python agent (agent/gt_agent.py).
//!
//! - `agent`: short, fixed actions ("setup" installs this computer's training packages once, after the
//!   owner agreed; "capabilities" reports hardware). Calls run one at a time.
//! - `worker_start` / `worker_stop` / `worker_state`: the long-running provider worker that connects
//!   OUTWARD to the GreenTokens server, asks for approved work, runs it and returns results.
//!
//! No Ray runs on provider computers and nothing here ever calls `ray stop`. Every argument is
//! validated here and again in Python. The provider key is passed through the environment, never on
//! the command line.

use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use serde_json::json;
use tauri::path::BaseDirectory;
use tauri::{AppHandle, Manager};

/// Exact version: every provider runs the same Python.
const PYTHON_VERSION: &str = "3.12.16";
const RUNTIME_MARKER: &str = "greentokens-runtime-v3";
const UV_RESOURCE: &str = if cfg!(windows) { "bin/uv.exe" } else { "bin/uv" };
const ACTIONS: &[&str] = &["setup", "capabilities"];

static AGENT_LOCK: Mutex<()> = Mutex::new(());
static WORKER: Mutex<Option<Child>> = Mutex::new(None);

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

fn worker_home(p: &Paths) -> PathBuf {
    p.data.join("worker")
}

fn command(program: &Path, p: &Paths) -> Command {
    let mut c = Command::new(program);
    c.env("UV_CACHE_DIR", p.data.join("uv-cache"));
    c.env("UV_PYTHON_INSTALL_DIR", p.data.join("python"));
    c.env("UV_PYTHON_PREFERENCE", "only-managed");
    c.env("UV_NO_CONFIG", "1");
    c.env("PYTHONUTF8", "1");
    c.env("GT_UV", &p.uv);
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

/// A private Python inside this app's data folder (training packages are added by the "setup" action).
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
    std::fs::write(&marker, b"ok").map_err(|_| "Can't write to this app's data folder.".to_string())?;
    Ok(())
}

pub fn valid_server(s: &str) -> bool {
    s.len() <= 200
        && (s.starts_with("https://") || s.starts_with("http://127.0.0.1"))
        && s.chars().all(|c| c.is_ascii_alphanumeric() || ".:/-_".contains(c))
}

pub fn valid_key(s: &str) -> bool {
    s.starts_with("gt_") && (23..=90).contains(&s.len()) && s.chars().all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
}

pub fn valid_device(s: &str) -> bool {
    (8..=64).contains(&s.len()) && s.chars().all(|c| c.is_ascii_alphanumeric() || c == '-')
}

#[tauri::command]
pub async fn agent(app: AppHandle, action: String) -> Result<serde_json::Value, String> {
    if !ACTIONS.contains(&action.as_str()) {
        return Err("Unknown action.".to_string());
    }
    tauri::async_runtime::spawn_blocking(move || run_agent(&app, &action))
        .await
        .map_err(|_| "The request was interrupted.".to_string())?
}

fn run_agent(app: &AppHandle, action: &str) -> Result<serde_json::Value, String> {
    let _guard = AGENT_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let p = paths(app)?;
    ensure_runtime(&p)?;
    let mut c = command(&p.python, &p);
    c.arg(&p.agent).arg(action);
    let stdout = run(c, "The GreenTokens agent")?;
    let line = stdout
        .lines()
        .rev()
        .find(|l| l.trim_start().starts_with('{'))
        .ok_or("The GreenTokens agent gave no answer.")?;
    serde_json::from_str(line).map_err(|_| "The GreenTokens agent gave an unreadable answer.".to_string())
}

#[tauri::command]
pub async fn worker_start(
    app: AppHandle,
    server: String,
    key: String,
    device_id: String,
    name: String,
) -> Result<serde_json::Value, String> {
    if !valid_server(&server) {
        return Err("The server address is invalid. Contact the operator for an updated installer.".to_string());
    }
    if !valid_key(&key) {
        return Err("Your session is invalid. Sign out and sign in again.".to_string());
    }
    if !valid_device(&device_id) {
        return Err("This computer's ID is invalid. Use Reset in Settings.".to_string());
    }
    let name: String = name.chars().filter(|c| !c.is_control()).take(64).collect();
    tauri::async_runtime::spawn_blocking(move || start_worker(&app, &server, &key, &device_id, &name))
        .await
        .map_err(|_| "The request was interrupted.".to_string())?
}

fn start_worker(app: &AppHandle, server: &str, key: &str, device: &str, name: &str) -> Result<serde_json::Value, String> {
    let _guard = AGENT_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let p = paths(app)?;
    ensure_runtime(&p)?;
    let mut slot = WORKER.lock().unwrap_or_else(|e| e.into_inner());
    if let Some(child) = slot.as_mut() {
        if let Ok(None) = child.try_wait() {
            return Ok(json!({ "ok": true, "running": true }));
        }
    }
    let home = worker_home(&p);
    std::fs::create_dir_all(&home).map_err(|_| "Can't write to this app's data folder.".to_string())?;
    let _ = std::fs::remove_file(home.join("worker.stop"));
    let _ = std::fs::remove_file(home.join("worker-state.json"));
    let mut c = command(&p.python, &p);
    c.arg(&p.agent)
        .arg("worker")
        .env("GT_SERVER", server)
        .env("GT_PROVIDER_KEY", key)
        .env("GT_DEVICE_ID", device)
        .env("GT_DEVICE_NAME", name)
        .env("GT_HOME", &home)
        .stdout(Stdio::null())
        .stderr(Stdio::null());
    let child = c.spawn().map_err(|_| "Could not start the GreenTokens worker.".to_string())?;
    *slot = Some(child);
    Ok(json!({ "ok": true, "running": true }))
}

/// Ask the worker to stop (it finishes cleanly); force it after 15 seconds.
fn stop_worker(app: &AppHandle) {
    let home = match paths(app) {
        Ok(p) => worker_home(&p),
        Err(_) => return,
    };
    let mut slot = WORKER.lock().unwrap_or_else(|e| e.into_inner());
    if let Some(mut child) = slot.take() {
        let _ = std::fs::create_dir_all(&home);
        let _ = std::fs::write(home.join("worker.stop"), b"stop");
        let deadline = Instant::now() + Duration::from_secs(15);
        while Instant::now() < deadline {
            if let Ok(Some(_)) = child.try_wait() {
                return;
            }
            std::thread::sleep(Duration::from_millis(250));
        }
        let _ = child.kill();
        let _ = child.wait();
    }
}

#[tauri::command]
pub async fn worker_stop(app: AppHandle) -> Result<serde_json::Value, String> {
    tauri::async_runtime::spawn_blocking(move || {
        stop_worker(&app);
        Ok::<serde_json::Value, String>(json!({ "ok": true, "running": false }))
    })
    .await
    .map_err(|_| "The request was interrupted.".to_string())?
}

#[tauri::command]
pub async fn worker_state(app: AppHandle) -> Result<serde_json::Value, String> {
    let p = paths(&app)?;
    let running = {
        let mut slot = WORKER.lock().unwrap_or_else(|e| e.into_inner());
        match slot.as_mut() {
            Some(child) => matches!(child.try_wait(), Ok(None)),
            None => false,
        }
    };
    let mut state = std::fs::read_to_string(worker_home(&p).join("worker-state.json"))
        .ok()
        .and_then(|text| serde_json::from_str::<serde_json::Value>(&text).ok())
        .unwrap_or_else(|| json!({ "state": "stopped" }));
    if let Some(object) = state.as_object_mut() {
        object.insert("running".to_string(), json!(running));
    }
    Ok(state)
}

/// Called when the window closes: stop sharing. (Never `ray stop`: providers don't run Ray.)
pub fn stop_on_exit(app: &AppHandle) {
    stop_worker(app);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validates_invite_parts() {
        assert!(valid_server("https://code-las-corps-agree.trycloudflare.com"));
        assert!(valid_server("http://127.0.0.1:8000"));
        assert!(!valid_server("http://example.com"));
        assert!(!valid_server("https://x.com/a b"));
        assert!(valid_key(&format!("gt_{}", "a".repeat(43))));
        assert!(!valid_key("gt_short"));
        assert!(!valid_key("gt_abcdefghijklmnopqrstuvwxyz; calc"));
        assert!(valid_device("0b1c2d3e-4f50-6172-8394-a5b6c7d8e9f0"));
        assert!(!valid_device("../../etc"));
    }
}
