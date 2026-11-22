//! Remembered sign-in, kept in the operating system's secure store
//! (Windows Credential Manager / macOS Keychain). Never written to plain files or logs.
//! The password is never stored: only the server's session token, which the app swaps
//! for a fresh one on each launch and deletes on sign-out.

use keyring::Entry;

const SERVICE: &str = "ai.greentokens.provider";
const ACCOUNT: &str = "provider-session";
const MAX_LEN: usize = 2048; // Windows credentials hold up to 2560 bytes.

fn entry() -> Result<Entry, String> {
    Entry::new(SERVICE, ACCOUNT).map_err(|_| "Secure storage is not available on this computer.".to_string())
}

/// Only a small JSON object with the expected fields is accepted.
fn valid(session: &str) -> bool {
    if session.len() > MAX_LEN {
        return false;
    }
    match serde_json::from_str::<serde_json::Value>(session) {
        Ok(serde_json::Value::Object(map)) => ["server", "token", "expires", "deviceId", "displayName"]
            .iter()
            .all(|key| map.contains_key(*key)),
        _ => false,
    }
}

async fn blocking<T: Send + 'static>(f: impl FnOnce() -> Result<T, String> + Send + 'static) -> Result<T, String> {
    tauri::async_runtime::spawn_blocking(f)
        .await
        .map_err(|_| "Secure storage did not respond.".to_string())?
}

#[tauri::command]
pub async fn session_save(session: String) -> Result<(), String> {
    if !valid(&session) {
        return Err("Invalid sign-in data.".to_string());
    }
    blocking(move || {
        entry()?
            .set_password(&session)
            .map_err(|_| "Could not remember this sign-in securely.".to_string())
    })
    .await
}

#[tauri::command]
pub async fn session_load() -> Result<Option<String>, String> {
    blocking(|| match entry()?.get_password() {
        Ok(session) if valid(&session) => Ok(Some(session)),
        // Missing, unreadable or malformed: behave as signed out.
        _ => Ok(None),
    })
    .await
}

#[tauri::command]
pub async fn session_clear() -> Result<(), String> {
    blocking(|| match entry()?.delete_credential() {
        Ok(()) | Err(keyring::Error::NoEntry) => Ok(()),
        Err(_) => Err("Could not remove the remembered sign-in.".to_string()),
    })
    .await
}

#[cfg(test)]
mod tests {
    use super::valid;

    #[test]
    fn accepts_only_small_complete_session_objects() {
        let ok = r#"{"server":"https://x.example","token":"gt_abc","expires":1,"deviceId":"device-01","displayName":"a"}"#;
        assert!(valid(ok));
        assert!(!valid(r#"{"token":"gt_abc"}"#));
        assert!(!valid("not json"));
        assert!(!valid(&format!(r#"{{"server":"{}","token":"t","expires":1,"deviceId":"d","displayName":"a"}}"#, "x".repeat(3000))));
    }
}
