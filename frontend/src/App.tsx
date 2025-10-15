import { useState, useEffect, useRef } from "react";
import "./App.css";
import { invoke } from "@tauri-apps/api/core";
import MessageComponent from "./components/MessageComponent";
import { open } from "@tauri-apps/plugin-dialog";
import { homeDir } from "@tauri-apps/api/path";

const API = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

// interacts with fast api to provide llm response to user's question
export async function search(q: string) {
  const res = await fetch(`${API}/search?q=` + encodeURIComponent(q));
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// function to check status of uvicorn server
export async function isServerUp(): Promise<boolean> {
  const res = await fetch(`${API}/status`);
  if (!res.ok) return false;

  const data = await res.json();
  return data.status === "running";
}

// opens user files for them to select the vault they want to use
export async function pickVault(): Promise<string | null> {
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
  type ServerStatus = "running" | "offline";
  const [serverStatus, setServerStatus] = useState<ServerStatus>("offline");

  // messages stored in chatlog
  type Message = { sender: "User" | "Ohara"; message: string };
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
    let tries = 1;
    const checkServerStatus = setInterval(async () => {
      if (!pythonLaunched.current) return; // don't check status if python not launched
      tries++;
      try {
        const status = await isServerUp();
        if (status) {
          console.log("Server Running");
          setServerStatus("running");
          clearInterval(checkServerStatus);
        }
      } catch (error) {
        // console.log("Status Check Failed: ", error);
      }

      // interval stops running (after a minute), main.py file is likely not being launched error should be prompted
      if (tries > 60) {
        console.log("stopped process");
        clearInterval(checkServerStatus);
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
    setServerStatus("offline");

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
          {serverStatus !== "running" ? (
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-current border-t-transparent" />
          ) : (
            <div>
              {chatlog.map((m, i) => (
                <MessageComponent
                  key={i}
                  sender={m.sender}
                  message={m.message}
                  citation={"citation" in m ? m.citation : undefined}
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
              serverStatus !== "running"
                ? "Starting server..."
                : "Type a message"
            }
            disabled={serverStatus !== "running"}
            className="w-full border border-white p-2 bg-black/70 backdrop-blur text-[#b8d2d3] focus:outline-none focus:ring-2 focus:ring-[#b8d2d3] font-['JetBrains_Mono',ui-monospace,monospace] text-sm rounded"
          />
        </div>
      </div>
    </>
  );
}

export default App;
