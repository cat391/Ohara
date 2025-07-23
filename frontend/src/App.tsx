import { useState, useEffect, useLayoutEffect, useRef } from "react";
import "./App.css";

function App() {
  // run npx tauri dev to run
  // color: #A9CFD1; , darker: [#66A9AD]
  const [userText, setUserText] = useState("");
  const [pxWidth, setPxWidth] = useState(0);
  const spanRef = useRef<HTMLSpanElement>(null);
  const maxPxWidth = 734;

  useLayoutEffect(() => {
    if (spanRef.current && spanRef.current.offsetWidth < maxPxWidth) {
      setPxWidth(spanRef.current.offsetWidth);
    }
  }, [userText]);

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
            style={{ width: pxWidth }}
            className="border-1 border-white p-0 bg-transparent text-[#b8d2d3] autofocus focus:outline-none focus:ring-2 focus:ring-[#b8d2d3]"
          ></input>
        </div>
      </div>
    </>
  );
}

export default App;
