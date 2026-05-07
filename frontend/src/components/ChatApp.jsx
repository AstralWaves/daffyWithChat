import React, { useEffect, useRef, useState, useCallback } from "react";
import { api, getWsUrl } from "../api";
import { useAuth } from "../AuthContext";
import Sidebar from "./Sidebar";
import ChatWindow from "./ChatWindow";
import CallModal from "./CallModal";

export default function ChatApp() {
  const { user } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState({}); // conv_id -> [messages]
  const [typingMap, setTypingMap] = useState({}); // conv_id -> {user_id: timeoutId}
  const [presence, setPresence] = useState({}); // user_id -> bool
  const [callState, setCallState] = useState(null); // { mode: 'incoming'|'outgoing'|'active', kind: 'audio'|'video', peer, offer? }

  const wsRef = useRef(null);
  const callStateRef = useRef(null);
  useEffect(() => { callStateRef.current = callState; }, [callState]);

  // Load conversations
  const loadConvs = useCallback(async () => {
    const res = await api.get("/conversations");
    setConversations(res.data);
    const p = {};
    res.data.forEach((c) => c.participants.forEach((u) => { p[u.id] = !!u.online; }));
    setPresence((prev) => ({ ...prev, ...p }));
  }, []);

  useEffect(() => { loadConvs(); }, [loadConvs]);

  // WebSocket connection
  useEffect(() => {
    const token = localStorage.getItem("auth_token");
    if (!token) return;
    const ws = new WebSocket(getWsUrl(token));
    wsRef.current = ws;

    ws.onmessage = (ev) => {
      const data = JSON.parse(ev.data);
      if (data.type === "message_new") {
        const m = data.message;
        setMessages((prev) => ({
          ...prev,
          [m.conversation_id]: [...(prev[m.conversation_id] || []), m],
        }));
        setConversations((prev) => {
          const idx = prev.findIndex((c) => c.id === m.conversation_id);
          if (idx === -1) { loadConvs(); return prev; }
          const c = { ...prev[idx], last_message: m, updated_at: m.created_at };
          if (m.sender_id !== user.id && activeIdRef.current !== m.conversation_id) {
            c.unread_count = (c.unread_count || 0) + 1;
          }
          return [c, ...prev.filter((_, i) => i !== idx)];
        });
        // auto mark read if active
        if (activeIdRef.current === m.conversation_id && m.sender_id !== user.id) {
          api.get(`/conversations/${m.conversation_id}/messages`).catch(() => {});
        }
      } else if (data.type === "conversation_new") {
        setConversations((prev) => {
          if (prev.some((c) => c.id === data.conversation.id)) return prev;
          return [data.conversation, ...prev];
        });
      } else if (data.type === "presence") {
        setPresence((prev) => ({ ...prev, [data.user_id]: data.online }));
      } else if (data.type === "typing") {
        setTypingMap((prev) => {
          const cm = { ...(prev[data.conversation_id] || {}) };
          if (cm[data.user_id]) clearTimeout(cm[data.user_id]);
          if (data.is_typing) {
            cm[data.user_id] = setTimeout(() => {
              setTypingMap((p) => {
                const nc = { ...(p[data.conversation_id] || {}) };
                delete nc[data.user_id];
                return { ...p, [data.conversation_id]: nc };
              });
            }, 3500);
          } else {
            delete cm[data.user_id];
          }
          return { ...prev, [data.conversation_id]: cm };
        });
      } else if (data.type === "messages_read") {
        setMessages((prev) => {
          const list = (prev[data.conversation_id] || []).map((m) =>
            m.sender_id === user.id && !m.read_by.includes(data.reader_id)
              ? { ...m, read_by: [...m.read_by, data.reader_id] }
              : m
          );
          return { ...prev, [data.conversation_id]: list };
        });
      } else if (data.type === "call_offer") {
        if (!callStateRef.current) {
          setCallState({
            mode: "incoming",
            kind: data.kind || "video",
            peer: data.peer,
            offer: data.offer,
            from_user_id: data.from_user_id,
          });
        }
      } else if (data.type === "call_answer") {
        window.dispatchEvent(new CustomEvent("call-signal", { detail: data }));
      } else if (data.type === "call_ice") {
        window.dispatchEvent(new CustomEvent("call-signal", { detail: data }));
      } else if (data.type === "call_end" || data.type === "call_reject") {
        window.dispatchEvent(new CustomEvent("call-signal", { detail: data }));
        setCallState(null);
      }
    };

    ws.onclose = () => { wsRef.current = null; };
    return () => { try { ws.close(); } catch (_) {} };
    // eslint-disable-next-line
  }, []);

  const activeIdRef = useRef(null);
  useEffect(() => { activeIdRef.current = activeId; }, [activeId]);

  const sendWs = (data) => {
    if (wsRef.current?.readyState === 1) wsRef.current.send(JSON.stringify(data));
  };

  const openConversation = async (convId) => {
    setActiveId(convId);
    try {
      const res = await api.get(`/conversations/${convId}/messages`);
      setMessages((prev) => ({ ...prev, [convId]: res.data }));
      setConversations((prev) =>
        prev.map((c) => (c.id === convId ? { ...c, unread_count: 0 } : c))
      );
    } catch (e) {}
  };

  const sendMessage = async (content, media, mediaType) => {
    if (!activeId) return;
    await api.post("/messages", { conversation_id: activeId, content, media, media_type: mediaType });
  };

  const startConversation = async (userIds, isGroup, name) => {
    const res = await api.post("/conversations", { user_ids: userIds, is_group: isGroup, name });
    setConversations((prev) => {
      if (prev.some((c) => c.id === res.data.id)) return prev;
      return [res.data, ...prev];
    });
    openConversation(res.data.id);
  };

  const startCall = (kind) => {
    const conv = conversations.find((c) => c.id === activeId);
    if (!conv || conv.is_group) return;
    const peer = conv.participants.find((u) => u.id !== user.id);
    if (!peer) return;
    setCallState({ mode: "outgoing", kind, peer });
  };

  const acceptCall = () => {
    setCallState((s) => s ? { ...s, mode: "active" } : s);
  };

  const endCall = () => {
    if (callState?.peer) {
      sendWs({ type: "call_end", target_user_id: callState.peer.id });
    }
    setCallState(null);
  };

  const activeConv = conversations.find((c) => c.id === activeId);

  return (
    <div className="h-screen w-screen flex bg-sand overflow-hidden">
      <Sidebar
        user={user}
        conversations={conversations}
        activeId={activeId}
        presence={presence}
        onOpen={openConversation}
        onStartConversation={startConversation}
      />
      <ChatWindow
        user={user}
        conversation={activeConv}
        messages={messages[activeId] || []}
        presence={presence}
        typingUsers={Object.keys(typingMap[activeId] || {})}
        onSend={sendMessage}
        onTyping={(typing) => sendWs({ type: "typing", conversation_id: activeId, is_typing: typing })}
        onCall={startCall}
      />
      {callState && (
        <CallModal
          state={callState}
          me={user}
          onAccept={acceptCall}
          onEnd={endCall}
          sendWs={sendWs}
        />
      )}
    </div>
  );
}
