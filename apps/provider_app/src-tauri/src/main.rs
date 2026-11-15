// Hide the console window in release builds on Windows.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod hardware;

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![hardware::detect_hardware])
        .run(tauri::generate_context!())
        .expect("error while running GreenTokens Provider");
}
