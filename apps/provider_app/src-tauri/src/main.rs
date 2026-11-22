// Hide the console window in release builds on Windows.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod agent;
mod hardware;
mod usage;

use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            hardware::detect_hardware,
            agent::agent,
            agent::worker_start,
            agent::worker_stop,
            agent::worker_state,
            usage::live_usage
        ])
        .on_window_event(|window, event| {
            // Stop sharing when the app closes; nothing keeps running in the background.
            if let tauri::WindowEvent::Destroyed = event {
                agent::stop_on_exit(window.app_handle());
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running GreenTokens Provider");
}
