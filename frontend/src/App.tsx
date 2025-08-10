import { useState, useEffect, useLayoutEffect, useRef } from "react";
import "./App.css";
import { invoke } from "@tauri-apps/api/core";
import MessageComponent from "./components/MessageComponent";

const API = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export async function search(q: string) {
  const res = await fetch(`${API}/search?q=` + encodeURIComponent(q));
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function App() {
  // run npx tauri dev to run
  // color: #A9CFD1; , darker: [#66A9AD]
  const [userText, setUserText] = useState("");
  const pythonLaunched = useRef(false);
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
    // python launched used to prevent multiple calls to start_python
    if (pythonLaunched.current) return;
    pythonLaunched.current = true;
    invoke("start_python")
      .then(() => console.log("Python launched"))
      .catch(console.error);
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
      const response = await search(userQuery);
      setChatlog((prev) => [...prev, { sender: "Ohara", message: response }]);
      console.log("Search complete: ", response);
    } catch (error) {
      console.log("Search failed: ", error);
    }
  };

  return (
    <>
      <div className="relative min-h-screen bg-black text-[#A9CFD1]">
        <div className="absolute inset-4 border border-current p-4 overflow-y-auto">
          {chatlog.map((m, i) => (
            <MessageComponent key={i} sender={m.sender} message={m.message} />
          ))}
        </div>
        <div className="absolute bottom-12 left-1/2 transform -translate-x-1/2">
          <input
            value={userText}
            onChange={(e) => setUserText(e.target.value)}
            onKeyDown={handleKeyDown}
            className="border border-white p-2 w-72 bg-transparent text-[#b8d2d3] focus:outline-none focus:ring-2 focus:ring-[#b8d2d3] font-['JetBrains_Mono',ui-monospace,monospace] text-sm"
          />
        </div>
      </div>
    </>
  );
}

export default App;
