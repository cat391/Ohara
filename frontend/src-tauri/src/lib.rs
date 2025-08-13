#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    process::{Child, Command},
    sync::Mutex,
};
use tauri::{generate_handler, Manager, WindowEvent};

struct PythonProcess(Mutex<Option<Child>>);

#[tauri::command]
fn start_python(
    app_handle: tauri::AppHandle,
    state: tauri::State<'_, PythonProcess>,
    vault_path: String,
) -> Result<(), String> {
    // Resolve main.py path
    let script = if cfg!(debug_assertions) {
        std::path::PathBuf::from("/Users/cole/Documents/Ohara/backend/main.py")
    } else {
        app_handle
            .path()
            .resource_dir()
            .map_err(|e| format!("resource_dir error: {e}"))? 
            .join("backend/main.py")
    };

    // Spawn Python (non-blocking)
    let child = Command::new("python3")
        .arg(&script)
        .arg("--vault")
        .arg(&vault_path)
        .spawn()
        .map_err(|e| format!("failed to launch python: {e}"))?;

    // Save handle (prevent double-spawn if you want)
    {
        let mut guard = state.0.lock().map_err(|e| e.to_string())?;
        *guard = Some(child);
    }
    Ok(())
}

pub fn run() {
    tauri::Builder::default()
        .manage(PythonProcess(Mutex::new(None)))
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(generate_handler![start_python])
        .on_window_event(|window, event| {
            let should_cleanup = matches!(
                event,
                WindowEvent::CloseRequested { .. } | WindowEvent::Destroyed
            );
            if should_cleanup {
                // Put the lock and its guard in their own scope so they drop early.
                {
                    let state: tauri::State<PythonProcess> = window.state();
                    if let Ok(mut guard) = state.0.lock() {
                        if let Some(mut child) = guard.take() {
                            // Try graceful terminate on Unix
                            #[cfg(unix)]
                            {
                                use nix::sys::signal::{kill, Signal::SIGTERM};
                                use nix::unistd::Pid;
                                let _ = kill(Pid::from_raw(child.id() as i32), SIGTERM);
                            }
                            // Fallback: hard kill (portable)
                            let _ = child.kill();
                            // Reap the process
                            let _ = child.wait();
                            println!("Python process terminated on window close.");
                        }
                    };
                }; 
            }
        })
        .setup(|_| Ok(()))
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
