//! Read-only hardware summary. Runs one fixed, bundled PowerShell/CIM script;
//! no user input reaches the command line, and no shell access is exposed to the UI.

#[cfg_attr(not(windows), allow(dead_code))]
const SCRIPT: &str = include_str!("detect_hardware.ps1");

#[tauri::command]
pub async fn detect_hardware() -> Result<serde_json::Value, String> {
    tauri::async_runtime::spawn_blocking(run)
        .await
        .map_err(|_| "Hardware detection was interrupted".to_string())?
}

#[cfg(windows)]
fn run() -> Result<serde_json::Value, String> {
    use std::os::windows::process::CommandExt;
    use std::process::{Command, Stdio};
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;

    let output = Command::new("powershell.exe")
        .args(["-NoProfile", "-NonInteractive", "-EncodedCommand", &encode_command(SCRIPT)])
        .stdin(Stdio::null())
        .creation_flags(CREATE_NO_WINDOW)
        .output()
        .map_err(|_| "Could not start Windows hardware detection".to_string())?;
    if !output.status.success() {
        return Err("Windows hardware detection failed".to_string());
    }
    let text = String::from_utf8_lossy(&output.stdout);
    serde_json::from_str(text.trim())
        .map_err(|_| "Hardware detection returned unreadable data".to_string())
}

#[cfg(target_os = "macos")]
fn run() -> Result<serde_json::Value, String> {
    use std::process::Command;

    fn text(program: &str, args: &[&str]) -> Option<String> {
        let out = Command::new(program).args(args).output().ok()?;
        if !out.status.success() {
            return None;
        }
        Some(String::from_utf8_lossy(&out.stdout).trim().to_string())
    }
    fn number(program: &str, args: &[&str]) -> f64 {
        text(program, args).and_then(|s| s.parse::<f64>().ok()).unwrap_or(0.0)
    }
    // "8 GB" / "1536 MB" -> bytes
    fn vram_bytes(s: &str) -> Option<f64> {
        let mut parts = s.split_whitespace();
        let value: f64 = parts.next()?.parse().ok()?;
        match parts.next()? {
            "GB" => Some(value * 1024.0 * 1024.0 * 1024.0),
            "MB" => Some(value * 1024.0 * 1024.0),
            _ => None,
        }
    }

    let mut gpus = Vec::new();
    if let Some(json) = text("system_profiler", &["SPDisplaysDataType", "-json"]) {
        if let Ok(value) = serde_json::from_str::<serde_json::Value>(&json) {
            if let Some(items) = value.get("SPDisplaysDataType").and_then(|v| v.as_array()) {
                for item in items {
                    let name = item.get("sppci_model").and_then(|v| v.as_str()).unwrap_or("").trim();
                    if name.is_empty() {
                        continue;
                    }
                    let vram = item.get("spdisplays_vram").and_then(|v| v.as_str()).and_then(vram_bytes);
                    gpus.push(serde_json::json!({ "name": name, "adapter_ram": 0, "registry_vram": vram }));
                }
            }
        }
    }
    let cpu = text("sysctl", &["-n", "machdep.cpu.brand_string"]).unwrap_or_default();
    let host = text("scutil", &["--get", "ComputerName"])
        .or_else(|| text("hostname", &[]))
        .unwrap_or_default();
    Ok(serde_json::json!({
        "cpu_model": cpu,
        "cores": number("sysctl", &["-n", "hw.physicalcpu"]),
        "threads": number("sysctl", &["-n", "hw.logicalcpu"]),
        "ram_bytes": number("sysctl", &["-n", "hw.memsize"]),
        "os": "macOS",
        "os_version": text("sw_vers", &["-productVersion"]).unwrap_or_default(),
        "hostname": host,
        "gpus": gpus,
    }))
}

#[cfg(not(any(windows, target_os = "macos")))]
fn run() -> Result<serde_json::Value, String> {
    Err("Hardware detection currently supports Windows and macOS only".to_string())
}

/// PowerShell -EncodedCommand expects Base64 of UTF-16LE text.
#[cfg_attr(not(windows), allow(dead_code))]
fn encode_command(script: &str) -> String {
    const TABLE: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let bytes: Vec<u8> = script.encode_utf16().flat_map(|unit| unit.to_le_bytes()).collect();
    let mut out = String::with_capacity(bytes.len().div_ceil(3) * 4);
    for chunk in bytes.chunks(3) {
        let b1 = chunk.get(1).copied().unwrap_or(0);
        let b2 = chunk.get(2).copied().unwrap_or(0);
        let n = (u32::from(chunk[0]) << 16) | (u32::from(b1) << 8) | u32::from(b2);
        for i in 0..4usize {
            if i <= chunk.len() {
                out.push(TABLE[((n >> (18 - 6 * i as u32)) & 63) as usize] as char);
            } else {
                out.push('=');
            }
        }
    }
    out
}

#[cfg(test)]
mod tests {
    #[test]
    fn encodes_like_powershell() {
        // [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes("ab")) == "YQBiAA=="
        assert_eq!(super::encode_command("ab"), "YQBiAA==");
        assert_eq!(super::encode_command("a"), "YQA=");
        assert_eq!(super::encode_command("abc"), "YQBiAGMA");
    }
}
