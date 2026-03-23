"use client";

import { useEffect, useRef, useState } from "react";
import { Button, Card, Chip, Spinner } from "@heroui/react";
import { createAdkSession, sendAdkMessage } from "../../api-actions";

type Role = "user" | "agent" | "error";
type Message = { id: string; role: Role; text: string };

const SESSION_ID = `web-${Math.random().toString(36).slice(2, 10)}`;

const QUICK_PROMPTS = [
  { label: "Planificar una clase",        emoji: "📝" },
  { label: "Validar una actividad",       emoji: "✅" },
  { label: "Explorar el programa EBI",    emoji: "📚" },
  { label: "Sugerir criterios de logro",  emoji: "🎯" },
];

// Minimal markdown renderer (bold, italic, code, headings, bullets)
function renderMarkdown(text: string): React.ReactNode[] {
  return text.split("\n").map((line, i) => {
    if (/^###\s/.test(line)) return <h4 key={i} className="font-bold text-sm mt-3 mb-1">{line.slice(4)}</h4>;
    if (/^##\s/.test(line))  return <h3 key={i} className="font-bold text-base mt-3 mb-1">{line.slice(3)}</h3>;
    if (/^#\s/.test(line))   return <h2 key={i} className="font-bold text-lg mt-3 mb-1">{line.slice(2)}</h2>;
    if (/^[-*]\s/.test(line)) return <li key={i} className="ml-4 list-disc text-sm leading-relaxed">{inline(line.slice(2))}</li>;
    if (/^\d+\.\s/.test(line)) return <li key={i} className="ml-4 list-decimal text-sm leading-relaxed">{inline(line.replace(/^\d+\.\s/, ""))}</li>;
    if (line.trim() === "") return <br key={i} />;
    return <p key={i} className="text-sm leading-relaxed">{inline(line)}</p>;
  });
}

function inline(text: string): React.ReactNode {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g).map((p, i) => {
    if (p.startsWith("**") && p.endsWith("**")) return <strong key={i}>{p.slice(2, -2)}</strong>;
    if (p.startsWith("`")  && p.endsWith("`"))  return <code key={i} className="bg-black/10 rounded px-1 font-mono text-xs">{p.slice(1, -1)}</code>;
    if (p.startsWith("*")  && p.endsWith("*"))  return <em key={i}>{p.slice(1, -1)}</em>;
    return p;
  });
}

export default function AsistenteTab() {
  const [messages, setMessages]       = useState<Message[]>([]);
  const [input, setInput]             = useState("");
  const [loading, setLoading]         = useState(false);
  const [sessionReady, setReady]      = useState(false);
  const bottomRef                     = useRef<HTMLDivElement>(null);
  const textareaRef                   = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    createAdkSession(SESSION_ID).then(() => setReady(true));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async (text: string) => {
    const t = text.trim();
    if (!t || loading || !sessionReady) return;
    setInput("");
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", text: t }]);
    setLoading(true);
    const reply = await sendAdkMessage(SESSION_ID, t);
    setMessages((prev) => [...prev, {
      id: crypto.randomUUID(),
      role: reply.startsWith("Error") ? "error" : "agent",
      text: reply,
    }]);
    setLoading(false);
  };

  const reset = () => {
    setMessages([]);
    createAdkSession(`web-${Math.random().toString(36).slice(2, 10)}`);
  };

  const onKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); }
  };

  return (
    <div className="flex flex-col h-full min-h-0">

      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-[var(--surface)] flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-danger/10 flex items-center justify-center text-danger">
            <ChatIcon />
          </div>
          <div>
            <p className="text-sm font-bold text-foreground">Facilitador Docente EBI</p>
            <p className="text-xs text-muted-foreground flex items-center gap-1">
              <span className={`w-1.5 h-1.5 rounded-full inline-block ${sessionReady ? "bg-success" : "bg-warning"}`} />
              {sessionReady ? "Agente listo" : "Conectando…"}
            </p>
          </div>
        </div>
        <Button variant="ghost" isIconOnly size="sm" onPress={reset} aria-label="Nueva sesión">
          <ResetIcon />
        </Button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 min-h-0">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-6 py-12">
            <div className="w-16 h-16 rounded-2xl bg-danger/10 flex items-center justify-center text-danger">
              <ChatIcon size={32} />
            </div>
            <div className="text-center">
              <p className="font-semibold text-foreground">Asistente Docente EBI</p>
              <p className="text-sm text-muted-foreground mt-1 max-w-xs">
                Preguntame sobre planificación, actividades, criterios de logro o el programa EBI.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2 w-full max-w-sm">
              {QUICK_PROMPTS.map((q) => (
                <button
                  key={q.label}
                  onClick={() => send(q.label)}
                  disabled={!sessionReady}
                  className="flex items-center gap-2 px-3 py-2.5 border border-border rounded-xl text-sm text-foreground hover:bg-muted disabled:opacity-50 transition-all text-left"
                >
                  <span>{q.emoji}</span>
                  <span className="text-xs font-medium">{q.label}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => <Bubble key={msg.id} message={msg} />)}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 pb-4 pt-3 border-t border-border bg-[var(--surface)] flex-shrink-0">
        <div className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKey}
            disabled={loading || !sessionReady}
            rows={1}
            placeholder={sessionReady ? "Escribí tu consulta… (Enter para enviar)" : "Conectando con el agente…"}
            className="flex-1 border border-border rounded-xl px-4 py-2.5 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-accent/40 bg-background text-foreground disabled:opacity-60"
            style={{ maxHeight: "120px", overflowY: "auto" }}
          />
          <Button
            variant="primary"
            isIconOnly
            isDisabled={loading || !sessionReady || !input.trim()}
            onPress={() => send(input)}
            aria-label="Enviar"
          >
            <SendIcon />
          </Button>
        </div>
        <p className="text-xs text-muted-foreground mt-1.5 ml-1">
          Shift+Enter para nueva línea · El agente tiene acceso al programa EBI
        </p>
      </div>
    </div>
  );
}

// ── Bubble ────────────────────────────────────────────────────────────────────

function Bubble({ message }: { message: Message }) {
  const isUser  = message.role === "user";
  const isError = message.role === "error";
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard.writeText(message.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[80%] flex flex-col gap-1 ${isUser ? "items-end" : "items-start"}`}>
        {isUser ? (
          <div className="px-4 py-3 rounded-2xl rounded-br-sm bg-accent text-accent-foreground text-sm leading-relaxed">
            {message.text}
          </div>
        ) : (
          <Card
            variant={isError ? "transparent" : "secondary"}
            className={`px-4 py-3 rounded-2xl rounded-bl-sm ${isError ? "border border-danger/30 text-danger" : ""}`}
          >
            <div className="space-y-1">{renderMarkdown(message.text)}</div>
          </Card>
        )}
        {!isUser && (
          <button
            onClick={copy}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors px-1"
          >
            {copied
              ? <><span className="text-success">✓</span> Copiado</>
              : <><CopyIcon /> Copiar</>
            }
          </button>
        )}
      </div>
    </div>
  );
}

// ── Typing indicator ──────────────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <Card variant="secondary" className="px-4 py-3 rounded-2xl rounded-bl-sm flex items-center gap-1">
        {[0, 150, 300].map((delay, i) => (
          <span
            key={i}
            className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"
            style={{ animationDelay: `${delay}ms` }}
          />
        ))}
      </Card>
    </div>
  );
}

// ── Iconos ────────────────────────────────────────────────────────────────────
function ChatIcon({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}
function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  );
}
function ResetIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10" /><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
    </svg>
  );
}
function CopyIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="13" height="13" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}
