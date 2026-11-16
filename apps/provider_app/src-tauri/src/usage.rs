//! Read-only live usage numbers for the Activity screen: whole-computer CPU and memory, the CPU used
//! by GreenTokens' own Ray workers, and GPU use. Nothing from the UI reaches a command line; the only
//! external commands are fixed strings (PowerShell GPU counter on Windows, `ioreg` on macOS).

use std::sync::{Mutex, OnceLock};
use std::time::{Duration, Instant};

use sysinfo::{ProcessRefreshKind, ProcessesToUpdate, System, UpdateKind};

/// Folder name of this app's private runtime. A process is "GreenTokens work" only if it is a Ray
/// worker started from that runtime.
const APP_FOLDER: &str = "ai.greentokens.provider";

struct Sampler {
    system: System,
    warmed: bool,
}

static SAMPLER: OnceLock<Mutex<Sampler>> = OnceLock::new();
/// Last GPU reading (percent), refreshed by a slow background thread. `None` = not measurable.
static GPU_CACHE: Mutex<Option<f64>> = Mutex::new(None);
/// When the UI last asked; the GPU thread only works while someone is watching.
static GPU_WANTED: Mutex<Option<Instant>> = Mutex::new(None);

/// True for a Ray worker process that belongs to this app's runtime (what training jobs run in).
pub fn is_greentokens_worker(command_line: &str) -> bool {
    let normalized = command_line.replace('\\', "/").to_lowercase();
    normalized.contains(APP_FOLDER) && normalized.contains("default_worker.py")
}

/// Windows: output of the GPU counter script, a single number such as `37.5`.
pub fn parse_number(text: &str) -> Option<f64> {
    text.trim().replace(',', ".").parse::<f64>().ok().map(|v| v.clamp(0.0, 100.0))
}

/// macOS: `"Device Utilization %"=12` inside the `PerformanceStatistics` of `ioreg` output.
#[cfg_attr(not(target_os = "macos"), allow(dead_code))]
pub fn parse_ioreg_gpu(text: &str) -> Option<f64> {
    let key = "\"Device Utilization %\"";
    let start = text.find(key)? + key.len();
    let rest = text[start..].trim_start().strip_prefix('=')?.trim_start();
    let digits: String = rest.chars().take_while(|c| c.is_ascii_digit() || *c == '.').collect();
    digits.parse::<f64>().ok().map(|v| v.min(100.0))
}

#[cfg(windows)]
fn read_gpu() -> Option<f64> {
    use std::os::windows::process::CommandExt;
    use std::process::{Command, Stdio};
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    // The same counter Task Manager shows; summed over all 3D engines. Fixed text, no user input.
    let script = "$s = (Get-Counter '\\GPU Engine(*engtype_3D)\\Utilization Percentage' -ErrorAction Stop).CounterSamples | Measure-Object -Property CookedValue -Sum; [math]::Round($s.Sum, 1)";
    let output = Command::new("powershell.exe")
        .args(["-NoProfile", "-NonInteractive", "-Command", script])
        .stdin(Stdio::null())
        .creation_flags(CREATE_NO_WINDOW)
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    parse_number(&String::from_utf8_lossy(&output.stdout))
}

#[cfg(target_os = "macos")]
fn read_gpu() -> Option<f64> {
    let output = std::process::Command::new("ioreg")
        .args(["-r", "-d", "1", "-w", "0", "-c", "IOAccelerator"])
        .output()
        .ok()?;
    parse_ioreg_gpu(&String::from_utf8_lossy(&output.stdout))
}

#[cfg(not(any(windows, target_os = "macos")))]
fn read_gpu() -> Option<f64> {
    None
}

fn ensure_gpu_thread() {
    static STARTED: OnceLock<()> = OnceLock::new();
    STARTED.get_or_init(|| {
        std::thread::spawn(|| loop {
            let wanted = GPU_WANTED
                .lock()
                .ok()
                .and_then(|guard| *guard)
                .map_or(false, |t| t.elapsed() < Duration::from_secs(15));
            if wanted {
                let value = read_gpu();
                if let Ok(mut cache) = GPU_CACHE.lock() {
                    *cache = value;
                }
            }
            std::thread::sleep(Duration::from_secs(3));
        });
    });
}

fn round1(v: f64) -> f64 {
    (v * 10.0).round() / 10.0
}

fn snapshot() -> Result<serde_json::Value, String> {
    ensure_gpu_thread();
    if let Ok(mut wanted) = GPU_WANTED.lock() {
        *wanted = Some(Instant::now());
    }
    let sampler = SAMPLER.get_or_init(|| Mutex::new(Sampler { system: System::new(), warmed: false }));
    let mut s = sampler.lock().map_err(|_| "Usage reading was interrupted".to_string())?;
    s.system.refresh_cpu_usage();
    s.system.refresh_memory();
    s.system.refresh_processes_specifics(
        ProcessesToUpdate::All,
        true,
        ProcessRefreshKind::nothing().with_cpu().with_cmd(UpdateKind::OnlyIfNotSet),
    );
    let cpus = s.system.cpus().len().max(1) as f64;
    let mut gt_cpu = 0.0_f64;
    let mut gt_processes = 0_u32;
    for process in s.system.processes().values() {
        let command_line = process.cmd().iter().map(|a| a.to_string_lossy()).collect::<Vec<_>>().join(" ");
        if is_greentokens_worker(&command_line) {
            gt_cpu += process.cpu_usage() as f64;
            gt_processes += 1;
        }
    }
    let warming_up = !s.warmed; // CPU % needs two samples; the first one is not meaningful
    s.warmed = true;
    const GIB: f64 = 1024.0 * 1024.0 * 1024.0;
    let gpu = GPU_CACHE.lock().ok().and_then(|g| *g);
    Ok(serde_json::json!({
        "cpu_percent": round1(s.system.global_cpu_usage() as f64),
        "ram_used_gb": round1(s.system.used_memory() as f64 / GIB),
        "ram_total_gb": round1(s.system.total_memory() as f64 / GIB),
        "greentokens_cpu_percent": round1((gt_cpu / cpus).min(100.0)),
        "greentokens_processes": gt_processes,
        "gpu_percent": gpu,
        "warming_up": warming_up,
    }))
}

#[tauri::command]
pub async fn live_usage() -> Result<serde_json::Value, String> {
    tauri::async_runtime::spawn_blocking(snapshot)
        .await
        .map_err(|_| "Usage reading was interrupted".to_string())?
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn recognises_only_this_apps_ray_workers() {
        assert!(is_greentokens_worker(
            r"C:\Users\a\AppData\Local\ai.greentokens.provider\runtime\Scripts\python.exe C:\Users\a\AppData\Local\ai.greentokens.provider\runtime\Lib\site-packages\ray\_private\workers\default_worker.py --node-ip-address=10.0.0.2"
        ));
        assert!(is_greentokens_worker(
            "/Users/a/Library/Application Support/ai.greentokens.provider/runtime/bin/python /Users/a/Library/Application Support/ai.greentokens.provider/runtime/lib/python3.12/site-packages/ray/_private/workers/default_worker.py"
        ));
        // Not ours: another Ray install, the app itself, an editor, other Python work.
        assert!(!is_greentokens_worker(r"C:\Python312\python.exe C:\other\ray\_private\workers\default_worker.py"));
        assert!(!is_greentokens_worker(r"C:\Program Files\GreenTokens Provider\greentokens-provider.exe"));
        assert!(!is_greentokens_worker("Code.exe --type=renderer"));
        assert!(!is_greentokens_worker(r"C:\Users\a\AppData\Local\ai.greentokens.provider\runtime\Scripts\python.exe -m pip list"));
    }

    #[test]
    fn parses_the_windows_gpu_counter_output() {
        assert_eq!(parse_number("37.5\r\n"), Some(37.5));
        assert_eq!(parse_number("12,5"), Some(12.5));
        assert_eq!(parse_number("250"), Some(100.0)); // summed engines can exceed 100
        assert_eq!(parse_number(""), None);
        assert_eq!(parse_number("Get-Counter : error"), None);
    }

    #[test]
    fn parses_the_apple_gpu_utilization_from_ioreg() {
        let text = r#"| |   "PerformanceStatistics" = {"Alloc system memory"=123,"Device Utilization %"=12,"Renderer Utilization %"=5}"#;
        assert_eq!(parse_ioreg_gpu(text), Some(12.0));
        assert_eq!(parse_ioreg_gpu(r#""Device Utilization %" = 7"#), Some(7.0));
        assert_eq!(parse_ioreg_gpu("no gpu here"), None);
    }
}
