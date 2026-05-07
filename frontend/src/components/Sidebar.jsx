import React, { useEffect, useState } from "react";
import { Search, Plus, LogOut, Users, X } from "lucide-react";
import { api } from "../api";
import { useAuth } from "../AuthContext";

const AVATAR_COLORS = [
  ["#C85A47", "#F9F8F6"],
  ["#38423B", "#F9F8F6"],
  ["#788A6F", "#F9F8F6"],
  ["#7A7A75", "#F9F8F6"],
  ["#1C1C1A", "#F9F8F6"],
];

export function Avatar({ name, online, size = 44, src }) {
  const initial = (name || "?").trim().charAt(0).toUpperCase();
  const idx = (name || "").charCodeAt(0) % AVATAR_COLORS.length;
  const [bg, fg] = AVATAR_COLORS[idx];
  return (
    <div className="relative inline-block" style={{ width: size, height: size }}>
      <div
        className="rounded-full flex items-center justify-center font-heading font-medium overflow-hidden"
        style={{ width: size, height: size, background: bg, color: fg, fontSize: size * 0.42 }}
      >
        {src ? <img src={src} alt="" className="w-full h-full object-cover" /> : initial}
      </div>
      {online && (
        <span
          className="absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-sidebar bg-sage"
          data-testid="online-indicator"
        />
      )}
    </div>
  );
}

function NewChatModal({ onClose, onStartConversation, currentUserId }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [selected, setSelected] = useState([]);
  const [groupName, setGroupName] = useState("");
  const [isGroup, setIsGroup] = useState(false);

  useEffect(() => {
    if (!q) { setResults([]); return; }
    const t = setTimeout(() => {
      api.get(`/users/search?q=${encodeURIComponent(q)}`).then((r) => setResults(r.data));
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  const toggle = (u) => {
    setSelected((prev) => prev.find((x) => x.id === u.id) ? prev.filter((x) => x.id !== u.id) : [...prev, u]);
  };

  const start = () => {
    if (selected.length === 0) return;
    const ids = selected.map((u) => u.id);
    onStartConversation(ids, isGroup || ids.length > 1, groupName || (ids.length > 1 ? selected.map((u)=>u.name).join(", ") : null));
    onClose();
  };

  return (
    <div className="fixed inset-0 z-40 bg-ink/40 backdrop-blur-sm flex items-center justify-center p-4" data-testid="new-chat-modal">
      <div className="bg-sand rounded-3xl w-full max-w-lg p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-heading font-medium">Start a conversation</h3>
          <button onClick={onClose} data-testid="close-new-chat" className="p-2 hover:bg-bordr rounded-full transition">
            <X size={18} />
          </button>
        </div>

        <div className="relative mb-4">
          <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-muted" />
          <input
            data-testid="user-search-input"
            autoFocus
            type="text"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search by username, email, or name…"
            className="w-full bg-white border border-bordr rounded-full pl-11 pr-4 py-3 text-sm focus:ring-2 focus:ring-terracotta/30 focus:border-terracotta"
          />
        </div>

        {selected.length > 0 && (
          <div className="flex gap-2 flex-wrap mb-3">
            {selected.map((u) => (
              <span key={u.id} className="flex items-center gap-2 bg-forest text-sand px-3 py-1.5 rounded-full text-sm">
                {u.name}
                <button onClick={() => toggle(u)}><X size={12} /></button>
              </span>
            ))}
          </div>
        )}

        {selected.length > 1 && (
          <input
            type="text"
            placeholder="Group name (optional)"
            value={groupName}
            onChange={(e) => setGroupName(e.target.value)}
            className="w-full bg-white border border-bordr rounded-full px-4 py-2.5 text-sm mb-3"
            data-testid="group-name-input"
          />
        )}

        <div className="max-h-64 overflow-y-auto space-y-1 mb-4">
          {results.length === 0 && q && <div className="text-sm text-muted p-4 text-center">No users found</div>}
          {results.map((u) => {
            const sel = !!selected.find((x) => x.id === u.id);
            return (
              <button
                key={u.id}
                data-testid={`search-result-${u.username}`}
                onClick={() => toggle(u)}
                className={`w-full flex items-center gap-3 p-3 rounded-2xl transition ${sel ? "bg-terracotta/10" : "hover:bg-bordr/50"}`}
              >
                <Avatar name={u.name} online={u.online} size={40} />
                <div className="flex-1 text-left">
                  <div className="font-medium text-sm">{u.name}</div>
                  <div className="text-xs text-muted">@{u.username}</div>
                </div>
                {sel && <div className="w-5 h-5 rounded-full bg-terracotta text-white text-xs flex items-center justify-center">✓</div>}
              </button>
            );
          })}
        </div>

        <button
          data-testid="start-chat-button"
          onClick={start}
          disabled={selected.length === 0}
          className="w-full bg-forest text-sand rounded-full py-3 font-medium disabled:opacity-40 hover:bg-ink transition"
        >
          {selected.length > 1 ? "Create group" : "Start chat"}
        </button>
      </div>
    </div>
  );
}

export default function Sidebar({ user, conversations, activeId, presence, onOpen, onStartConversation }) {
  const [showNew, setShowNew] = useState(false);
  const { logout } = useAuth();
  const [filter, setFilter] = useState("");

  const getOther = (c) => c.participants.find((u) => u.id !== user.id);
  const titleOf = (c) => c.is_group ? (c.name || c.participants.map((p) => p.name).join(", ")) : (getOther(c)?.name || "Chat");

  const filtered = conversations.filter((c) => titleOf(c).toLowerCase().includes(filter.toLowerCase()));

  return (
    <aside className="w-[360px] flex-shrink-0 bg-sidebar border-r border-bordr flex flex-col" data-testid="sidebar">
      {/* Header */}
      <div className="p-6 pb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Avatar name={user.name} online src={user.avatar} size={42} />
          <div>
            <div className="text-xs uppercase tracking-[0.2em] text-muted font-semibold">Signed in</div>
            <div className="font-heading font-medium text-base text-ink truncate max-w-[160px]" data-testid="current-username">{user.name}</div>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            data-testid="new-chat-button"
            onClick={() => setShowNew(true)}
            className="w-9 h-9 rounded-full bg-terracotta text-sand flex items-center justify-center hover:bg-terracottaHover transition"
            title="New chat"
          >
            <Plus size={18} />
          </button>
          <button
            data-testid="logout-button"
            onClick={logout}
            className="w-9 h-9 rounded-full hover:bg-bordr text-muted flex items-center justify-center transition"
            title="Sign out"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="px-6 pb-3">
        <div className="relative">
          <Search size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-muted" />
          <input
            data-testid="conversation-search-input"
            type="text"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Search conversations"
            className="w-full bg-white/70 focus:bg-white border-0 rounded-full pl-10 pr-4 py-2.5 text-sm transition focus:ring-1 focus:ring-terracotta/30"
          />
        </div>
      </div>

      <div className="px-6 mt-2 mb-1 text-xs uppercase tracking-[0.25em] text-muted font-semibold">
        Conversations
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto pb-4">
        {filtered.length === 0 && (
          <div className="px-6 py-12 text-center text-sm text-muted">
            <div className="font-heading text-base text-ink mb-1">No threads yet</div>
            Tap <span className="text-terracotta font-semibold">+</span> to begin
          </div>
        )}
        {filtered.map((c) => {
          const other = getOther(c);
          const online = c.is_group ? false : (other ? presence[other.id] || other.online : false);
          const isActive = c.id === activeId;
          const last = c.last_message;
          return (
            <button
              data-testid={`conversation-item-${c.id}`}
              key={c.id}
              onClick={() => onOpen(c.id)}
              className={`w-full flex items-center gap-3 p-3 mx-2 rounded-2xl transition text-left ${isActive ? "bg-white shadow-sm" : "hover:bg-white/50"}`}
            >
              {c.is_group ? (
                <div className="w-11 h-11 rounded-full bg-forest text-sand flex items-center justify-center">
                  <Users size={18} />
                </div>
              ) : (
                <Avatar name={other?.name || "?"} online={online} size={44} />
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-medium text-sm text-ink truncate">{titleOf(c)}</div>
                  {last && <div className="text-[10px] text-muted whitespace-nowrap">{formatTime(last.created_at)}</div>}
                </div>
                <div className="flex items-center justify-between gap-2 mt-0.5">
                  <div className="text-xs text-muted truncate">
                    {last ? (last.media ? "📷 Photo" : last.content) : "Say hello"}
                  </div>
                  {c.unread_count > 0 && (
                    <span className="bg-terracotta text-white text-[10px] font-bold px-2 py-0.5 rounded-full" data-testid={`unread-${c.id}`}>
                      {c.unread_count}
                    </span>
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {showNew && (
        <NewChatModal
          onClose={() => setShowNew(false)}
          onStartConversation={onStartConversation}
          currentUserId={user.id}
        />
      )}
    </aside>
  );
}

function formatTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}
