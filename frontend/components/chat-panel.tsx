"use client";

import { useEffect, useState } from "react";
import { Send } from "lucide-react";
import type { ChatMessage } from "@/lib/types";

export function ChatPanel({ enabled, initialMessages }: { enabled: boolean; initialMessages: ChatMessage[] }) {
  const [messages, setMessages] = useState<ChatMessage[]>(enabled ? initialMessages : []);
  const [draft, setDraft] = useState("");

  useEffect(() => {
    setMessages(enabled ? initialMessages : []);
  }, [enabled, initialMessages]);

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const question = draft.trim();
    if (!question || !enabled) return;
    setDraft("");
    setMessages((current) => [
      ...current,
      { id: `u-${Date.now()}`, role: "user", content: question },
      {
        id: `a-${Date.now()}`,
        role: "assistant",
        content: "Based on this run, the supervisor would answer by reusing the completed agent evidence and the stored workflow context.",
      },
    ]);
  }

  return (
    <section className="rounded-xl border border-line bg-panel shadow-soft">
      <div className="border-b border-line p-4">
        <h2 className="text-sm font-semibold">Chat</h2>
      </div>
      <div className="thin-scrollbar grid max-h-[340px] gap-3 overflow-y-auto p-4">
        {messages.length > 0 ? (
          messages.map((message) => (
            <div
              key={message.id}
              className={`max-w-[92%] rounded-lg px-3 py-2 text-sm leading-6 ${
                message.role === "user" ? "ml-auto bg-ink text-white" : "bg-slate-50 text-slate-700"
              }`}
            >
              {message.content}
            </div>
          ))
        ) : (
          <div className="rounded-lg bg-slate-50 px-3 py-2 text-sm leading-6 text-muted">
            {enabled ? "The supervisor result is ready. Ask a follow-up about fundamentals, technicals, news, or the final rating." : "Chat becomes available after the supervisor completes."}
          </div>
        )}
      </div>
      <form onSubmit={submit} className="flex gap-2 border-t border-line p-3">
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          disabled={!enabled}
          placeholder={enabled ? "Ask follow-up" : "Available after supervisor"}
          className="min-w-0 flex-1 rounded-lg border border-line px-3 text-sm outline-none disabled:bg-slate-50"
        />
        <button
          type="submit"
          disabled={!enabled}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-ink text-white disabled:bg-slate-300"
          aria-label="Send"
        >
          <Send size={16} />
        </button>
      </form>
    </section>
  );
}
