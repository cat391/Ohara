#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    sync::Mutex,
    thread::sleep,
    time::{Duration, Instant},
};
use tauri::{generate_handler, Manager, WindowEvent};
use tauri_plugin_shell::process::CommandChild;
#[cfg(not(debug_assertions))]
use tauri_plugin_shell::{process::CommandEvent, ShellExt};

#[allow(dead_code)] // one variant is unused per build profile (dev vs release)
enum Backend {
    /// Dev mode: system python3 running backend/main.py from the repo checkout
    Dev(std::process::Child),
    /// Release: the bundled PyInstaller sidecar binary
    Sidecar(CommandChild),
}

struct BackendProcess(Mutex<Option<Backend>>);

#[cfg(unix)]
fn send_sigterm(pid: i32) {
    use nix::sys::signal::{kill, Signal::SIGTERM};
    use nix::unistd::Pid;
    let _ = kill(Pid::from_raw(pid), SIGTERM);
}

#[cfg(debug_assertions)]
fn find_dev_python() -> String {
    // Prefer the repo venv — the system python3 won't have the backend deps
    let base = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    for rel in ["../../.venv/bin/python3", "../../../.venv/bin/python3"] {
        let p = base.join(rel);
        if p.exists() {
            return p.display().to_string();
        }
    }
    "python3".to_string()
}

#[cfg(debug_assertions)]
fn find_dev_script() -> Result<std::path::PathBuf, String> {
    let base = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"));
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

fn stop_backend(backend: Backend) {
    match backend {
        Backend::Dev(mut child) => {
            // try graceful terminate on Unix
            #[cfg(unix)]
            send_sigterm(child.id() as i32);

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
        Backend::Sidecar(child) => {
            // graceful SIGTERM first so uvicorn can shut down cleanly
            #[cfg(unix)]
            {
                send_sigterm(child.pid() as i32);
                sleep(Duration::from_millis(800));
            }
            // hard kill; errors if it already exited, which is fine
            let _ = child.kill();
        }
    }
}

#[tauri::command]
fn start_python(
    app_handle: tauri::AppHandle,
    state: tauri::State<'_, BackendProcess>,
    vault_path: String,
) -> Result<(), String> {
    // 1) Take any existing child out (release the lock before waiting)
    let old_backend = {
        let mut guard = state.0.lock().map_err(|e| e.to_string())?;
        guard.take()
    };
    if let Some(backend) = old_backend {
        stop_backend(backend);
    }

    // 2) Spawn the backend: repo python3 in dev, bundled sidecar in release
    #[cfg(debug_assertions)]
    let backend = {
        let script = find_dev_script()?;
        let child = std::process::Command::new(find_dev_python())
            .arg(&script)
            .arg("--vault")
            .arg(&vault_path)
            .spawn()
            .map_err(|e| format!("failed to launch python: {e}"))?;
        Backend::Dev(child)
    };

    #[cfg(not(debug_assertions))]
    let backend = {
        let (mut rx, child) = app_handle
            .shell()
            .sidecar("ohara-backend")
            .map_err(|e| format!("sidecar not found: {e}"))?
            .args(["--vault", &vault_path])
            .spawn()
            .map_err(|e| format!("failed to launch backend: {e}"))?;

        // forward backend output to the app log so release issues are debuggable
        tauri::async_runtime::spawn(async move {
            while let Some(event) = rx.recv().await {
                match event {
                    CommandEvent::Stdout(line) | CommandEvent::Stderr(line) => {
                        log::info!("[backend] {}", String::from_utf8_lossy(&line));
                    }
                    CommandEvent::Terminated(payload) => {
                        log::info!("[backend] exited: {:?}", payload.code);
                    }
                    _ => {}
                }
            }
        });
        Backend::Sidecar(child)
    };

    // silence unused warning in debug builds (app_handle is only used for the sidecar)
    #[cfg(debug_assertions)]
    let _ = &app_handle;

    // 3) Store handle
    {
        let mut guard = state.0.lock().map_err(|e| e.to_string())?;
        *guard = Some(backend);
    }
    Ok(())
}

#[tauri::command]
fn stop_python(state: tauri::State<'_, BackendProcess>) -> Result<(), String> {
    if let Some(backend) = {
        let mut guard = state.0.lock().map_err(|e| e.to_string())?;
        guard.take()
    } {
        stop_backend(backend);
    }
    Ok(())
}

pub fn run() {
    tauri::Builder::default()
        .manage(BackendProcess(Mutex::new(None)))
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_log::Builder::default().build())
        .invoke_handler(generate_handler![start_python, stop_python])
        .on_window_event(|window, event| {
            if matches!(event, WindowEvent::CloseRequested { .. } | WindowEvent::Destroyed) {
                if let Some(backend) = {
                    let state: tauri::State<BackendProcess> = window.state();
                    state.0.lock().ok().and_then(|mut g| g.take())
                } {
                    stop_backend(backend);
                    println!("Backend process terminated on window close.");
                }
            }
        })
        .setup(|_| Ok(()))
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
