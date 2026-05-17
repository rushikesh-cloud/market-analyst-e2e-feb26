"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Send } from "lucide-react";
import { chatWithSupervisorRun } from "@/lib/api";
import { MarkdownMessage } from "@/components/markdown-message";
import type { ChatMessage } from "@/lib/types";

type TypingBubbleProps = {
  active: boolean;
};

function TypingBubble({ active }: TypingBubbleProps) {
  return (
    <div
      aria-live="polite"
      aria-label="Supervisor is generating a response"
      className={`max-w-[92%] rounded-lg bg-slate-50 px-3 py-3 text-slate-700 transition ${active ? "opacity-100" : "opacity-0"}`}
    >
      <div className="flex items-center gap-1">
        {[0, 1, 2].map((index) => (
          <span
            // A simple staggered loader reads well in a compact chat rail.
            key={index}
            className="h-2 w-2 rounded-full bg-slate-400 animate-[pulse_1.1s_ease-in-out_infinite]"
            style={{ animationDelay: `${index * 0.18}s` }}
          />
        ))}
      </div>
    </div>
  );
}

export function ChatPanel({
  runId,
  enabled,
  initialMessages,
}: {
  runId: string;
  enabled: boolean;
  initialMessages: ChatMessage[];
}) {
  const [messages, setMessages] = useState<ChatMessage[]>(enabled ? initialMessages : []);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const wasEnabledRef = useRef(enabled);

  useEffect(() => {
    const wasEnabled = wasEnabledRef.current;
    if (!enabled) {
      setMessages([]);
      setPending(false);
      setError(null);
    } else if (!wasEnabled && initialMessages.length > 0) {
      setMessages(initialMessages);
    }
    wasEnabledRef.current = enabled;
  }, [enabled, initialMessages]);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;
    container.scrollTop = container.scrollHeight;
  }, [messages, pending, error]);

  const hasConversation = useMemo(() => messages.length > 0 || pending || Boolean(error), [messages, pending, error]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const question = draft.trim();
    if (!question || !enabled || pending) return;
    const nextUserMessage: ChatMessage = { id: `u-${Date.now()}`, role: "user", content: question };
    setDraft("");
    setError(null);
    setPending(true);
    setMessages((current) => [...current, nextUserMessage]);

    try {
      const currentHistory = [...messages, nextUserMessage].map(({ role, content }) => ({ role, content }));
      const response = await chatWithSupervisorRun(runId, {
        message: question,
        history: currentHistory.slice(0, -1),
      });
      setMessages(
        response.history.map((item, index) => ({
          id: `${item.role}-${index}-${Date.now()}`,
          role: item.role,
          content: item.content,
        })),
      );
    } catch (apiError) {
      setError(apiError instanceof Error ? apiError.message : "Unable to get supervisor chat response");
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="flex min-h-[420px] flex-col rounded-xl border border-line bg-panel shadow-soft xl:h-[calc(100vh-10rem)] xl:max-h-[760px]">
      <div className="border-b border-line p-4">
        <h2 className="text-sm font-semibold">Chat</h2>
      </div>
      <div ref={scrollContainerRef} className="thin-scrollbar flex-1 space-y-3 overflow-y-auto p-4">
        {hasConversation ? (
          messages.map((message) => (
            <div
              key={message.id}
              className={`max-w-[92%] rounded-lg px-3 py-2 text-sm leading-6 ${
                message.role === "user" ? "ml-auto bg-ink text-white" : "bg-slate-50 text-slate-700"
              }`}
            >
              {message.role === "assistant" ? (
                <MarkdownMessage content={message.content} />
              ) : (
                <MarkdownMessage content={message.content} inverted />
              )}
            </div>
          ))
        ) : (
          <div className="rounded-lg bg-slate-50 px-3 py-2 text-sm leading-6 text-muted">
            {enabled ? "Ask a follow-up about fundamentals, technicals, news, or the final rating." : "Chat becomes available after the supervisor completes."}
          </div>
        )}
        {pending ? <TypingBubble active /> : null}
        {error ? <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm leading-6 text-red-700">{error}</div> : null}
      </div>
      <form onSubmit={submit} className="sticky bottom-0 mt-auto flex gap-2 border-t border-line bg-panel p-3">
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          disabled={!enabled || pending}
          placeholder={enabled ? "Ask follow-up" : "Available after supervisor"}
          className="min-w-0 flex-1 rounded-lg border border-line px-3 text-sm outline-none disabled:bg-slate-50"
        />
        <button
          type="submit"
          disabled={!enabled || pending}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-ink text-white disabled:bg-slate-300"
          aria-label="Send"
        >
          <Send size={16} />
        </button>
      </form>
    </section>
  );
}
