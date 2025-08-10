import { useState, useEffect, useLayoutEffect, useRef } from "react";
import "./App.css";
import { invoke } from "@tauri-apps/api/core";

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
  const [pxWidth, setPxWidth] = useState(0);
  const spanRef = useRef<HTMLSpanElement>(null);
  const maxPxWidth = 734;
  const pythonLaunched = useRef(false);

  // on app load, launch the main.py file
  useEffect(() => {
    // python launched used to prevent multiple calls to start_python
    if (pythonLaunched.current) return;
    pythonLaunched.current = true;
    invoke("start_python")
      .then(() => console.log("Python launched"))
      .catch(console.error);
  }, []);

  useLayoutEffect(() => {
    if (spanRef.current && spanRef.current.offsetWidth < maxPxWidth) {
      setPxWidth(spanRef.current.offsetWidth);
    }
  }, [userText]);

  const handleKeyDown = (e: any): string | void => {
    if (e.key !== "Enter") return;
    const userQuery = userText;

    setUserText("");

    const response = search(userQuery);
    console.log(response);

    return "Complete";
  };

  return (
    <>
      <div className="relative min-h-screen bg-black text-[#A9CFD1]">
        <div className="absolute inset-4 border-1 border-current pointer-events-none" />
        <div className="relative p-8">
          <p className="text-[#66A9AD]">
            Current Directory: test/directory, !settings to change
          </p>
          <span
            ref={spanRef}
            className="font-sans text-[#b8d2d3] invisible absolute whitespace-pre p-2"
          >
            {userText || " "}
          </span>
          <input
            value={userText}
            onChange={(e) => setUserText(e.target.value)}
            onKeyDown={handleKeyDown}
            style={{ width: pxWidth }}
            className="border-1 border-white p-0 bg-transparent text-[#b8d2d3] autofocus focus:outline-none focus:ring-2 focus:ring-[#b8d2d3]"
          ></input>
        </div>
      </div>
    </>
  );
}

export default App;
