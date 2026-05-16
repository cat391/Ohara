import { useState, useEffect, useRef } from "react";
import "./App.css";
import MessageComponent from "./components/MessageComponent";

const API = import.meta.env.VITE_API_URL ?? "";

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

function App() {
  const [userText, setUserText] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const [responseLoading, setResponseLoading] = useState(false);

  // variables for server checking
  type ServerStatus = "running" | "offline";
  const [serverStatus, setServerStatus] = useState<ServerStatus>("offline");

  // messages stored in chatlog
  type Source = { file_name: string; path: string; score?: number };
  type Message = { sender: "User" | "Ohara"; message: string; citation?: Source[] };
  const [chatlog, setChatlog] = useState<Message[]>([]);

  // on mount, poll /status until backend is ready
  useEffect(() => {
    let cancelled = false;
    const interval = setInterval(async () => {
      try {
        const up = await isServerUp();
        if (up && !cancelled) {
          console.log("Server Running");
          setServerStatus("running");
          clearInterval(interval);
        }
      } catch {
        // server not ready yet
      }
    }, 1000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // Upon enter, search fast api for response and update chatlog with response
  const handleKeyDown = async (
    e: React.KeyboardEvent<HTMLInputElement>
  ): Promise<void> => {
    if (e.key !== "Enter") return;

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
