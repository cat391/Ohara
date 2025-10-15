#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    path::PathBuf,
    process::{Child, Command},
    sync::Mutex,
    thread::sleep,
    time::{Duration, Instant},
};
use tauri::{generate_handler, Manager, WindowEvent};

struct PythonProcess(Mutex<Option<Child>>);

fn python_cmd() -> &'static str {
    #[cfg(windows)]
    { "python" }
    #[cfg(not(windows))]
    { "python3" }
}

fn find_dev_script() -> Result<PathBuf, String> {
    let base = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let candidates = [
        "../backend/main.py",
        "../../backend/main.py",    
        "../../../backend/main.py",
    ];
    for rel in candidates {
        let p = base.join(rel);
        if p.exists() {
            return Ok(p);
        }
    }
    let tried = candidates
        .iter()
        .map(|r| base.join(r).display().to_string())
        .collect::<Vec<_>>()
        .join("\n");
    Err(format!("main.py not found. Tried:\n{tried}"))
}

fn stop_child_if_running(mut child: Child) {
    // try graceful terminate on Unix
    #[cfg(unix)]
    {
        use nix::sys::signal::{kill, Signal::SIGTERM};
        use nix::unistd::Pid;
        let _ = kill(Pid::from_raw(child.id() as i32), SIGTERM);
    }

    // wait a short grace period
    let deadline = Instant::now() + Duration::from_millis(800);
    while Instant::now() < deadline {
        if let Ok(Some(_status)) = child.try_wait() {
            return;
        }
        sleep(Duration::from_millis(50));
    }

    // hard kill + reap
    let _ = child.kill();
    let _ = child.wait();
}

#[tauri::command]
fn start_python(
    app_handle: tauri::AppHandle,
    state: tauri::State<'_, PythonProcess>,
    vault_path: String, 
) -> Result<(), String> {
    // 1) Take any existing child out (release the lock before waiting)
    let old_child = {
        let mut guard = state.0.lock().map_err(|e| e.to_string())?;
        guard.take()
    };
    if let Some(child) = old_child {
        stop_child_if_running(child);
    }

    // 2) Resolve script path
    let script = if cfg!(debug_assertions) {
        find_dev_script()?
    } else {
        app_handle
            .path()
            .resource_dir()
            .map_err(|e| format!("resource_dir error: {e}"))?
            .join("backend/main.py")
    };

    // 3) Spawn new Python
    let child = Command::new("python3")
        .arg(&script)
        .arg("--vault")
        .arg(&vault_path)
        .spawn()
        .map_err(|e| format!("failed to launch python: {e}"))?;

    // 4) Store handle
    {
        let mut guard = state.0.lock().map_err(|e| e.to_string())?;
        *guard = Some(child);
    }
    Ok(())
}

#[tauri::command]
fn stop_python(state: tauri::State<'_, PythonProcess>) -> Result<(), String> {
    if let Some(child) = {
        let mut guard = state.0.lock().map_err(|e| e.to_string())?;
        guard.take()
    } {
        stop_child_if_running(child);
    }
    Ok(())
}

pub fn run() {
    tauri::Builder::default()
        .manage(PythonProcess(Mutex::new(None)))
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(generate_handler![start_python, stop_python])
        .on_window_event(|window, event| {
            if matches!(event, WindowEvent::CloseRequested { .. } | WindowEvent::Destroyed) {
                if let Some(child) = {
                    let state: tauri::State<PythonProcess> = window.state();
                    state.0.lock().ok().and_then(|mut g| g.take())
                } {
                    stop_child_if_running(child);
                    println!("Python process terminated on window close.");
                }
            }
        })
        .setup(|_| Ok(()))
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
