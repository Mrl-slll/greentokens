//! Read-only hardware summary. Runs one fixed, bundled PowerShell/CIM script;
//! no user input reaches the command line, and no shell access is exposed to the UI.

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

#[cfg(not(windows))]
fn run() -> Result<serde_json::Value, String> {
    Err("Hardware detection currently supports Windows only".to_string())
}

/// PowerShell -EncodedCommand expects Base64 of UTF-16LE text.
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
