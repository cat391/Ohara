type MessageProps = {
  sender?: string;
  message: string;
};

export default function MessageComponent({
  sender = "Ohara",
  message,
}: MessageProps) {
  return (
    <p
      className={
        sender === "Ohara"
          ? "text-[#66A9AD] font-['JetBrains_Mono',ui-monospace,monospace] text-sm"
          : "text-[#b8d2d3] font-['JetBrains_Mono',ui-monospace,monospace] text-sm"
      }
    >
      {sender}: {message}
    </p>
  );
}
