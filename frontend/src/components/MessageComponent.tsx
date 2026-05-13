import { useState } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";

type Source = { file_name: string; path: string; score?: number };
type MessageProps = {
  sender: string;
  message: string;
  citation?: Source[] | null;
};

export default function MessageComponent({ sender, message, citation }: MessageProps) {
  const [open, setOpen] = useState(false);
  const hasCitations = citation && citation.length > 0;
  const msgColor = sender === "Ohara" ? "text-[#66A9AD]" : "text-[#b8d2d3]";

  return (
    <div className="font-['JetBrains_Mono',ui-monospace,monospace] text-sm">
      <p className={msgColor}>
        {sender}: {message}
        {hasCitations && (
          <>
            {" "}
            {open ? (
              <>
                {citation.map((src, i) => (
                  <span key={i}>
                    <a
                      title={src.score !== undefined ? `Similarity: ${(src.score * 100).toFixed(1)}%` : undefined}
                      className="text-[#524459] hover:text-[#bb9dc9] transition-colors cursor-pointer"
                      onClick={async (e) => {
                        e.preventDefault();
                        try {
                          await openUrl("obsidian://open?path=" + encodeURIComponent(src.path));
                        } catch (err) {
                          console.error("Failed to open Obsidian link:", err);
                        }
                      }}
                    >
                      [{src.file_name}]
                    </a>
                    {i < citation.length - 1 && " "}
                  </span>
                ))}
                {" "}
                <button
                  className="text-[#524459] hover:text-[#bb9dc9] transition-colors"
                  onClick={() => setOpen(false)}
                >
                  [-]
                </button>
              </>
            ) : (
              <button
                className="text-[#524459] hover:text-[#bb9dc9] transition-colors"
                onClick={() => setOpen(true)}
              >
                [+] Sources ({citation.length})
              </button>
            )}
          </>
        )}
      </p>
    </div>
  );
}
