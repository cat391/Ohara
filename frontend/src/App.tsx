import { useState, useEffect, useRef } from "react";
import "./App.css";
import { invoke } from "@tauri-apps/api/core";
import MessageComponent from "./components/MessageComponent";
import { open } from "@tauri-apps/plugin-dialog";
import { homeDir } from "@tauri-apps/api/path";

const API = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

// interacts with fast api to provide llm response to user's question
async function search(q: string) {
  const res = await fetch(`${API}/search?q=` + encodeURIComponent(q));
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// startup phases reported by the backend's /status endpoint
type ServerPhase =
  | "offline"
  | "starting"
  | "downloading"
  | "loading"
  | "indexing"
  | "running"
  | "error";
type ServerStatus = { phase: ServerPhase; progress: number; detail: string };

const OFFLINE: ServerStatus = { phase: "offline", progress: 0, detail: "" };

// function to check status of uvicorn server
async function getServerStatus(): Promise<ServerStatus | null> {
  try {
    const res = await fetch(`${API}/status`);
    if (!res.ok) return null;
    const data = await res.json();
    return {
      phase: data.status as ServerPhase,
      progress: data.progress ?? 0,
      detail: data.detail ?? "",
    };
  } catch {
    return null;
  }
}

function phaseLabel(status: ServerStatus): string {
  switch (status.phase) {
    case "downloading":
      return `Downloading AI models (one-time) — ${Math.round(status.progress * 100)}%`;
    case "loading":
      return "Loading language model…";
    case "indexing":
      return "Indexing your vault…";
    default:
      return "Starting Ohara…";
  }
}

// opens user files for them to select the vault they want to use
async function pickVault(): Promise<string | null> {
  const initial = await homeDir();
  const selected = await open({
    title: "Select your Obsidian vault folder",
    directory: true,
    multiple: false,
    defaultPath: initial,
  });
  // `open` returns `string | string[] | null`
  return typeof selected === "string" ? selected : null;
}

function App() {
  // run npx tauri dev to run
  // color: #A9CFD1; , darker: [#66A9AD]
  const [userText, setUserText] = useState("");
  const pythonLaunched = useRef(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [responseLoading, setResponseLoading] = useState(false);

  // variables for server checking
  const [serverStatus, setServerStatus] = useState<ServerStatus>(OFFLINE);

  // messages stored in chatlog
  type Source = { file_name: string; path: string; score?: number };
  type Message = { sender: "User" | "Ohara"; message: string; citation?: Source[] };
  const [chatlog, setChatlog] = useState<Message[]>([]);

  const selectVault = async () => {
    const vaultPath = await pickVault();
    if (!vaultPath) return;

    if (pythonLaunched.current) return;
    pythonLaunched.current = true;

    setChatlog((prev) => [
      ...prev,
      {
        sender: "Ohara",
        message: `Current Directory ~ ${vaultPath}, type "!vault" to change`,
      },
    ]);

    await invoke("start_python", { vaultPath })
      .then(() => console.log("Python launched"))
      .catch(console.error);

    // add a fall back system if user exits out of file selector
  };

  const checkServerStatus = () => {
    // Poll until the backend reports running or error. No try cap: the
    // first-run model download takes minutes and /status reports its progress.
    const interval = setInterval(async () => {
      if (!pythonLaunched.current) return; // don't check status if python not launched

      const status = await getServerStatus();
      if (!status) return; // server not up yet, keep polling

      setServerStatus(status);
      if (status.phase === "running" || status.phase === "error") {
        clearInterval(interval);
      }
    }, 1000);
  };

  // on app load, launch the main.py file
  useEffect(() => {
    // select vault
    (async () => {
      await selectVault();
    })();

    checkServerStatus();
  }, []);

  // change vault
  const handleChangeVault = async () => {
    await invoke("stop_python");
    pythonLaunched.current = false;
    setServerStatus(OFFLINE);

    await selectVault();
    checkServerStatus();
  };

  // Upon enter, search fast api for response and update chatlog with response
  const handleKeyDown = async (
    e: React.KeyboardEvent<HTMLInputElement>
  ): Promise<void> => {
    if (e.key !== "Enter") return;

    if (userText.toLowerCase().trim() === "!vault") {
      handleChangeVault();
      setUserText("");
      return;
    }

    const userQuery = userText;

    setUserText("");

    setChatlog((prev) => [...prev, { sender: "User", message: userQuery }]);

    setResponseLoading(true);

    try {
      const { answer, sources } = await search(userQuery);
      setChatlog((prev) => [
        ...prev,
        { sender: "Ohara", message: answer, citation: sources },
      ]);
      console.log("Search complete: ", answer, sources);
      setResponseLoading(false);
    } catch (error) {
      console.log("Search failed: ", error);
      setResponseLoading(false);
    }
  };

  // auto-scroll to bottom when messages change
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [chatlog, serverStatus]);

  return (
    <>
      <div className="relative min-h-screen bg-black text-[#A9CFD1]">
        <div
          ref={scrollRef}
          className="absolute inset-4 border border-current p-4 overflow-y-auto pb-28 no-scrollbar"
        >
          {serverStatus.phase !== "running" ? (
            serverStatus.phase === "error" ? (
              <p className="text-sm font-['JetBrains_Mono',ui-monospace,monospace]">
                Something went wrong starting Ohara: {serverStatus.detail}
              </p>
            ) : (
              <div className="flex flex-col items-start gap-3">
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-current border-t-transparent" />
                <p className="text-sm font-['JetBrains_Mono',ui-monospace,monospace]">
                  {phaseLabel(serverStatus)}
                </p>
                {serverStatus.phase === "downloading" && (
                  <div className="w-full max-w-sm h-2 border border-current rounded overflow-hidden">
                    <div
                      className="h-full bg-[#66A9AD] transition-all duration-500"
                      style={{ width: `${Math.round(serverStatus.progress * 100)}%` }}
                    />
                  </div>
                )}
              </div>
            )
          ) : (
            <div>
              {chatlog.map((m, i) => (
                <MessageComponent
                  key={i}
                  sender={m.sender}
                  message={m.message}
                  citation={m.citation}
                />
              ))}
              {responseLoading && (
                <div className="h-3 w-3 text-[#66A9AD] animate-spin rounded-full border-2 border-current border-t-transparent" />
              )}
            </div>
          )}
        </div>

        <div className="fixed bottom-12 left-1/2 -translate-x-1/2 z-50 w-full max-w-xl px-6">
          <input
            value={userText}
            onChange={(e) => setUserText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              serverStatus.phase !== "running"
                ? "Starting server..."
                : "Type a message"
            }
            disabled={serverStatus.phase !== "running"}
            className="w-full border border-white p-2 bg-black/70 backdrop-blur text-[#b8d2d3] focus:outline-none focus:ring-2 focus:ring-[#b8d2d3] font-['JetBrains_Mono',ui-monospace,monospace] text-sm rounded"
          />
        </div>
      </div>
    </>
  );
}

export default App;
