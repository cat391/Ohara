type MessageProps = {
  sender: string;
  message: string;
  citation?: any;
};

export default function MessageComponent({
  sender,
  message,
  citation,
}: MessageProps) {
  console.log(citation);
  return (
    <p
      className={
        sender === "Ohara"
          ? "text-[#66A9AD] font-['JetBrains_Mono',ui-monospace,monospace] text-sm"
          : "text-[#b8d2d3] font-['JetBrains_Mono',ui-monospace,monospace] text-sm"
      }
    >
      {sender}: {message}
      {citation ? (
        <a
          title={citation[0].path}
          role="button"
          tabIndex={0}
          className="cursor-pointer text-[#524459] hover:text-[#bb9dc9] transition-colors"
        >
          [{citation[0].file_name}]
        </a>
      ) : null}
    </p>
  );
}
