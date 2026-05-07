import React, { useEffect, useRef, useState } from "react";
import { Send, Image as ImageIcon, Phone, Video, Check, CheckCheck } from "lucide-react";
import { Avatar } from "./Sidebar";

const EMPTY_IMG =
  "https://images.unsplash.com/photo-1760622728583-b51cf72e9987?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2NDF8MHwxfHNlYXJjaHwxfHxtaW5pbWFsaXN0JTIwemVuJTIwZ2FyZGVuJTIwY2FsbSUyMGVtcHR5fGVufDB8fHx8MTc3ODE4Njg5OHww&ixlib=rb-4.1.0&q=85";

function sameDay(a, b) {
  if (!a || !b) return false;
  const da = new Date(a), db = new Date(b);
  return da.getFullYear() === db.getFullYear() && da.getMonth() === db.getMonth() && da.getDate() === db.getDate();
}

function dateLabel(iso) {
  const d = new Date(iso);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yest = new Date(today); yest.setDate(today.getDate() - 1);
  const dDay = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  if (dDay.getTime() === today.getTime()) return "Today";
  if (dDay.getTime() === yest.getTime()) return "Yesterday";
  const days = (today - dDay) / (1000 * 60 * 60 * 24);
  if (days < 7) return d.toLocaleDateString([], { weekday: "long" });
  return d.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" });
}

export default function ChatWindow({ user, conversation, messages, presence, typingUsers, onSend, onTyping, onCall }) {
  const [text, setText] = useState("");
  const [media, setMedia] = useState(null);
  const fileRef = useRef(null);
  const feedRef = useRef(null);
  const typingTimer = useRef(null);

  useEffect(() => {
    if (feedRef.current) feedRef.current.scrollTop = feedRef.current.scrollHeight;
  }, [messages, conversation?.id]);

  if (!conversation) {
    return (
      <div className="flex-1 flex items-center justify-center bg-sand p-12 relative">
        <div className="text-center max-w-md relative z-10">
          <div className="overflow-hidden rounded-3xl mb-8 border border-bordr">
            <img src={EMPTY_IMG} alt="" className="w-full h-64 object-cover" />
          </div>
          <div className="text-xs uppercase tracking-[0.3em] text-terracotta font-semibold mb-3">Ember</div>
          <h2 className="text-3xl font-heading font-medium text-ink mb-3">Pick a thread, or start one.</h2>
          <p className="text-muted leading-relaxed">
            Search someone, send a message, place a call. Quiet on the surface, real-time underneath.
          </p>
        </div>
      </div>
    );
  }

  const other = conversation.participants.find((u) => u.id !== user.id);
  const title = conversation.is_group
    ? (conversation.name || conversation.participants.map((p) => p.name).join(", "))
    : (other?.name || "Chat");
  const online = conversation.is_group ? false : (other ? (presence[other.id] ?? other.online) : false);
  const subtitle = typingUsers.length > 0
    ? "typing…"
    : conversation.is_group
      ? `${conversation.participants.length} people`
      : online ? "Active now" : "Offline";

  const handleType = (v) => {
    setText(v);
    onTyping(true);
    if (typingTimer.current) clearTimeout(typingTimer.current);
    typingTimer.current = setTimeout(() => onTyping(false), 1500);
  };

  const submit = async (e) => {
    e?.preventDefault();
    if (!text.trim() && !media) return;
    const t = text;
    const m = media;
    setText("");
    setMedia(null);
    onTyping(false);
    await onSend(t, m?.data, m?.type);
  };

  const onFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 5 * 1024 * 1024) { alert("Image must be under 5MB"); return; }
    const reader = new FileReader();
    reader.onload = () => setMedia({ data: reader.result, type: "image" });
    reader.readAsDataURL(f);
  };

  return (
    <main className="flex-1 flex flex-col bg-sand relative" data-testid="chat-window">
      {/* Header */}
      <header className="flex items-center justify-between p-6 border-b border-bordr bg-sand/90 backdrop-blur-md sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <Avatar name={title} online={online} size={42} />
          <div>
            <div className="font-heading font-medium text-lg text-ink leading-tight" data-testid="chat-title">{title}</div>
            <div className="text-xs text-muted flex items-center gap-1.5">
              {!conversation.is_group && online && <span className="w-1.5 h-1.5 rounded-full bg-sage inline-block" />}
              {subtitle}
            </div>
          </div>
        </div>
        {!conversation.is_group && (
          <div className="flex items-center gap-2">
            <button
              data-testid="audio-call-button"
              onClick={() => onCall("audio")}
              className="w-10 h-10 rounded-full hover:bg-bordr/60 text-ink flex items-center justify-center transition"
              title="Audio call"
            >
              <Phone size={18} strokeWidth={1.6} />
            </button>
            <button
              data-testid="video-call-button"
              onClick={() => onCall("video")}
              className="w-10 h-10 rounded-full hover:bg-bordr/60 text-ink flex items-center justify-center transition"
              title="Video call"
            >
              <Video size={18} strokeWidth={1.6} />
            </button>
          </div>
        )}
      </header>

      {/* Messages */}
      <div ref={feedRef} className="flex-1 overflow-y-auto px-6 py-6 flex flex-col gap-3" data-testid="message-feed">
        {messages.map((m, i) => {
          const mine = m.sender_id === user.id;
          const prev = messages[i - 1];
          const showAvatar = !mine && (!prev || prev.sender_id !== m.sender_id);
          const readByOthers = m.read_by.filter((id) => id !== user.id).length > 0;
          const showDateSep = !prev || !sameDay(prev.created_at, m.created_at);
          return (
            <React.Fragment key={m.id}>
              {showDateSep && (
                <div className="flex items-center justify-center my-2">
                  <span className="text-[10px] uppercase tracking-[0.25em] text-muted bg-bordr/40 px-3 py-1 rounded-full">
                    {dateLabel(m.created_at)}
                  </span>
                </div>
              )}
              <div
                data-testid={`message-${m.id}`}
                className={`flex anim-msg ${mine ? "justify-end" : "justify-start"} items-end gap-2`}
              >
              {!mine && (
                <div className="w-8">
                  {showAvatar && <Avatar name={m.sender_name} size={28} />}
                </div>
              )}
              <div className={`max-w-[72%] flex flex-col ${mine ? "items-end" : "items-start"}`}>
                {!mine && conversation.is_group && showAvatar && (
                  <div className="text-[11px] text-muted ml-2 mb-1">{m.sender_name}</div>
                )}
                <div
                  className={`px-4 py-2.5 shadow-sm ${
                    mine
                      ? "bg-forest text-sand rounded-2xl rounded-br-md"
                      : "bg-white text-ink border border-bordr rounded-2xl rounded-bl-md"
                  }`}
                >
                  {m.media && m.media_type === "image" && (
                    <img src={m.media} alt="" className="rounded-xl max-w-xs max-h-80 mb-1" />
                  )}
                  {m.content && <div className="whitespace-pre-wrap break-words text-[15px] leading-relaxed">{m.content}</div>}
                </div>
                <div className={`flex items-center gap-1 mt-1 px-1 text-[10px] text-muted`}>
                  <span>{new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                  {mine && (readByOthers ? <CheckCheck size={12} className="text-terracotta" /> : <Check size={12} />)}
                </div>
              </div>
            </div>
            </React.Fragment>
          );
        })}
        {typingUsers.length > 0 && (
          <div className="flex items-center gap-2" data-testid="typing-indicator">
            <div className="bg-white border border-bordr rounded-2xl px-4 py-3 flex items-center gap-1">
              <span className="typing-dot w-1.5 h-1.5 bg-muted rounded-full inline-block" />
              <span className="typing-dot w-1.5 h-1.5 bg-muted rounded-full inline-block" />
              <span className="typing-dot w-1.5 h-1.5 bg-muted rounded-full inline-block" />
            </div>
          </div>
        )}
        {messages.length === 0 && (
          <div className="flex-1 flex items-center justify-center text-center text-muted text-sm">
            No messages yet. Send the first one.
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={submit} className="p-6 border-t border-bordr bg-sand">
        {media && (
          <div className="mb-3 relative inline-block">
            <img src={media.data} alt="" className="rounded-xl max-h-32 border border-bordr" />
            <button type="button" onClick={() => setMedia(null)} className="absolute -top-2 -right-2 bg-ink text-sand rounded-full w-6 h-6 text-xs">×</button>
          </div>
        )}
        <div className="flex items-center gap-2 bg-white border border-bordr p-1.5 rounded-full shadow-sm">
          <input
            type="file"
            accept="image/*"
            ref={fileRef}
            onChange={onFile}
            className="hidden"
            data-testid="file-input"
          />
          <button
            type="button"
            data-testid="attach-image-button"
            onClick={() => fileRef.current?.click()}
            className="w-10 h-10 rounded-full hover:bg-bordr text-muted flex items-center justify-center transition"
          >
            <ImageIcon size={18} strokeWidth={1.6} />
          </button>
          <input
            data-testid="message-input"
            type="text"
            value={text}
            onChange={(e) => handleType(e.target.value)}
            placeholder="Write something…"
            className="flex-1 bg-transparent border-0 px-3 py-2 text-[15px] focus:outline-none"
          />
          <button
            type="submit"
            data-testid="send-message-button"
            disabled={!text.trim() && !media}
            className="w-10 h-10 rounded-full bg-terracotta text-sand flex items-center justify-center hover:bg-terracottaHover transition disabled:opacity-30"
          >
            <Send size={16} strokeWidth={2} />
          </button>
        </div>
      </form>
    </main>
  );
}
