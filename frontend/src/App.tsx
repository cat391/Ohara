import { useState, useEffect, useRef } from "react";
import "./App.css";
import { invoke } from "@tauri-apps/api/core";
import MessageComponent from "./components/MessageComponent";

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

function App() {
  // run npx tauri dev to run
  // color: #A9CFD1; , darker: [#66A9AD]
  const [userText, setUserText] = useState("");
  const pythonLaunched = useRef(false);

  // variables for server checking
  type ServerStatus = "running" | "offline";
  const [serverStatus, setServerStatus] = useState<ServerStatus>("offline");

  // messages stored in chatlog
  type Message = { sender: "User" | "Ohara"; message: string };
  const [chatlog, setChatlog] = useState<Message[]>([
    {
      sender: "Ohara",
      message: "Current Directory ~ TEST, !settings to change",
    },
  ]);

  // on app load, launch the main.py file
  useEffect(() => {
    // python launched reference used to prevent multiple calls to start_python
    if (pythonLaunched.current) return;
    pythonLaunched.current = true;
    invoke("start_python")
      .then(() => console.log("Python launched"))
      .catch(console.error);

    // constant check to see if the uvicorn server is up and running
    let tries = 1;
    const checkServerStatus = setInterval(async () => {
      tries++;
      try {
        const status = await isServerUp();
        if (status) {
          console.log("Server Running");
          setServerStatus("running");
          clearInterval(checkServerStatus);
        }
      } catch (error) {
        console.log("Status Check Failed: ", error);
      }

      // interval stops running, main.py file is likely not being launched error should be prompted
      if (tries > 30) {
        console.log("stopped process");
        clearInterval(checkServerStatus);
      }
    }, 1000);
  }, []);

  // Upon enter, search fast api and update messages
  const handleKeyDown = async (
    e: React.KeyboardEvent<HTMLInputElement>
  ): Promise<void> => {
    if (e.key !== "Enter") return;
    const userQuery = userText;

    setUserText("");

    setChatlog((prev) => [...prev, { sender: "User", message: userQuery }]);

    try {
      const { answer, sources } = await search(userQuery);
      setChatlog((prev) => [
        ...prev,
        { sender: "Ohara", message: answer, citation: sources },
      ]);
      console.log("Search complete: ", answer, sources);
    } catch (error) {
      console.log("Search failed: ", error);
    }
  };

  // when server starts, load up stuff

  return (
    <>
      <div className="relative min-h-screen bg-black text-[#A9CFD1]">
        <div className="absolute inset-4 border border-current p-4 overflow-y-auto">
          {serverStatus !== "running" ? (
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-current border-t-transparent" />
          ) : (
            <>
              <div>
                {" "}
                {chatlog.map((m, i) => (
                  <MessageComponent
                    key={i}
                    sender={m.sender}
                    message={m.message}
                    citation={"citation" in m ? m.citation : undefined}
                  />
                ))}
                <div className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
              </div>

              <div className="absolute bottom-12 left-1/2 transform -translate-x-1/2">
                <input
                  value={userText}
                  onChange={(e) => setUserText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="border border-white p-2 w-72 bg-transparent text-[#b8d2d3] focus:outline-none focus:ring-2 focus:ring-[#b8d2d3] font-['JetBrains_Mono',ui-monospace,monospace] text-sm"
                />
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}

export default App;
