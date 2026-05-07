import React, { useEffect, useState } from "react";
import { X, UserPlus, Check, XCircle, UserMinus } from "lucide-react";
import { api } from "../api";
import { Avatar } from "./Sidebar";

export default function FriendsModal({ onClose, onStartChat, currentUser }) {
  const [tab, setTab] = useState("friends"); // friends | requests | search
  const [friends, setFriends] = useState([]);
  const [requests, setRequests] = useState([]);
  const [q, setQ] = useState("");
  const [searchResults, setSearchResults] = useState([]);

  const loadAll = async () => {
    const [fr, rq] = await Promise.all([
      api.get("/friends").then((r) => r.data),
      api.get("/friends/requests").then((r) => r.data),
    ]);
    setFriends(fr);
    setRequests(rq);
  };

  useEffect(() => { loadAll(); }, []);

  useEffect(() => {
    if (!q) { setSearchResults([]); return; }
    const t = setTimeout(async () => {
      const r = await api.get(`/users/search?q=${encodeURIComponent(q)}`);
      setSearchResults(r.data);
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  const sendRequest = async (uid) => {
    await api.post("/friends/request", { target_user_id: uid });
    setSearchResults((prev) => prev.map((u) => u.id === uid ? { ...u, friendship_status: "pending_out" } : u));
    loadAll();
  };

  const accept = async (uid) => {
    await api.post("/friends/accept", { target_user_id: uid });
    loadAll();
  };

  const reject = async (uid) => {
    await api.post("/friends/reject", { target_user_id: uid });
    loadAll();
  };

  const removeFriend = async (uid) => {
    if (!window.confirm("Remove this friend?")) return;
    await api.delete(`/friends/${uid}`);
    loadAll();
  };

  const Btn = ({ onClick, children, variant = "primary", testid }) => (
    <button
      onClick={onClick}
      data-testid={testid}
      className={`text-xs px-3 py-1.5 rounded-full font-medium transition ${
        variant === "primary"
          ? "bg-terracotta text-sand hover:bg-terracottaHover"
          : variant === "ghost"
            ? "bg-bordr/60 text-ink hover:bg-bordr"
            : "bg-forest text-sand hover:bg-ink"
      }`}
    >
      {children}
    </button>
  );

  return (
    <div className="fixed inset-0 z-40 bg-ink/40 backdrop-blur-sm flex items-center justify-center p-4" data-testid="friends-modal">
      <div className="bg-sand rounded-3xl w-full max-w-lg p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-heading font-medium">People</h3>
          <button onClick={onClose} data-testid="close-friends-modal" className="p-2 hover:bg-bordr rounded-full">
            <X size={18} />
          </button>
        </div>

        <div className="flex gap-1 bg-bordr/60 p-1 rounded-full mb-4 text-sm">
          {[
            { k: "friends", label: `Friends ${friends.length ? `(${friends.length})` : ""}` },
            { k: "requests", label: `Requests${requests.length ? ` · ${requests.length}` : ""}` },
            { k: "search", label: "Find people" },
          ].map((t) => (
            <button
              key={t.k}
              data-testid={`friends-tab-${t.k}`}
              onClick={() => setTab(t.k)}
              className={`flex-1 py-2 rounded-full font-medium transition ${tab === t.k ? "bg-sand text-ink shadow-sm" : "text-muted hover:text-ink"}`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="max-h-[60vh] overflow-y-auto">
          {tab === "friends" && (
            <div className="space-y-1">
              {friends.length === 0 && <div className="text-sm text-muted text-center py-8">No friends yet. Find people!</div>}
              {friends.map((u) => (
                <div key={u.id} className="flex items-center gap-3 p-3 rounded-2xl hover:bg-white/60">
                  <Avatar name={u.name} online={u.online} src={u.avatar} size={42} />
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm truncate">{u.name}</div>
                    <div className="text-xs text-muted">@{u.username}{u.bio ? ` · ${u.bio}` : ""}</div>
                  </div>
                  <Btn testid={`chat-friend-${u.username}`} onClick={() => { onStartChat([u.id], false, null); onClose(); }}>Chat</Btn>
                  <button onClick={() => removeFriend(u.id)} data-testid={`remove-friend-${u.username}`} className="text-muted hover:text-terracotta p-1.5">
                    <UserMinus size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}

          {tab === "requests" && (
            <div className="space-y-1">
              {requests.length === 0 && <div className="text-sm text-muted text-center py-8">No pending requests</div>}
              {requests.map((r) => (
                <div key={r.request.id} className="flex items-center gap-3 p-3 rounded-2xl hover:bg-white/60">
                  <Avatar name={r.from_user.name} src={r.from_user.avatar} size={42} />
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm truncate">{r.from_user.name}</div>
                    <div className="text-xs text-muted">wants to be friends</div>
                  </div>
                  <Btn testid={`accept-request-${r.from_user.username}`} variant="forest" onClick={() => accept(r.from_user.id)}>
                    <Check size={12} className="inline mr-1" />Accept
                  </Btn>
                  <Btn testid={`reject-request-${r.from_user.username}`} variant="ghost" onClick={() => reject(r.from_user.id)}>
                    <XCircle size={12} className="inline mr-1" />Decline
                  </Btn>
                </div>
              ))}
            </div>
          )}

          {tab === "search" && (
            <div>
              <input
                data-testid="friends-search-input"
                type="text"
                autoFocus
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search by username, email, or name…"
                className="w-full bg-white border border-bordr rounded-full px-4 py-2.5 text-sm mb-3 focus:ring-2 focus:ring-terracotta/30"
              />
              <div className="space-y-1">
                {searchResults.length === 0 && q && <div className="text-sm text-muted text-center py-6">No users found</div>}
                {searchResults.map((u) => {
                  const s = u.friendship_status;
                  return (
                    <div key={u.id} className="flex items-center gap-3 p-3 rounded-2xl hover:bg-white/60">
                      <Avatar name={u.name} online={u.online} src={u.avatar} size={42} />
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm truncate">{u.name}</div>
                        <div className="text-xs text-muted">@{u.username}</div>
                      </div>
                      {s === "friends" && <span className="text-xs text-sage font-semibold">Friends</span>}
                      {s === "pending_out" && <span className="text-xs text-muted">Requested</span>}
                      {s === "pending_in" && (
                        <Btn testid={`accept-search-${u.username}`} onClick={() => accept(u.id)}>Accept</Btn>
                      )}
                      {s === "none" && (
                        <Btn testid={`add-friend-${u.username}`} onClick={() => sendRequest(u.id)}>
                          <UserPlus size={12} className="inline mr-1" />Add
                        </Btn>
                      )}
                      <Btn testid={`chat-search-${u.username}`} variant="ghost" onClick={() => { onStartChat([u.id], false, null); onClose(); }}>Chat</Btn>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
