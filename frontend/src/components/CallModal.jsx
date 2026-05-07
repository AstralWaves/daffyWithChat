import React, { useEffect, useRef, useState } from "react";
import { Phone, PhoneOff, Mic, MicOff, Video, VideoOff } from "lucide-react";
import { Avatar } from "./Sidebar";

const ICE_SERVERS = [
  { urls: "stun:stun.l.google.com:19302" },
  { urls: "stun:stun1.l.google.com:19302" },
];

export default function CallModal({ state, me, onAccept, onEnd, sendWs }) {
  const { mode, kind, peer, offer, from_user_id } = state;
  const [muted, setMuted] = useState(false);
  const [cameraOff, setCameraOff] = useState(false);
  const [status, setStatus] = useState(mode === "incoming" ? "Incoming…" : mode === "outgoing" ? "Calling…" : "Connecting…");
  const [mediaError, setMediaError] = useState(null);
  const localRef = useRef(null);
  const remoteRef = useRef(null);
  const pcRef = useRef(null);
  const localStreamRef = useRef(null);
  const remoteStreamRef = useRef(null);
  const pendingIceRef = useRef([]);

  // Setup peer connection
  useEffect(() => {
    let cancelled = false;
    const setup = async () => {
      const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
      pcRef.current = pc;

      const remoteStream = new MediaStream();
      remoteStreamRef.current = remoteStream;
      if (remoteRef.current) remoteRef.current.srcObject = remoteStream;

      pc.ontrack = (e) => {
        e.streams[0].getTracks().forEach((t) => remoteStream.addTrack(t));
        if (remoteRef.current) remoteRef.current.srcObject = remoteStream;
        setStatus("Connected");
      };

      pc.onicecandidate = (e) => {
        if (e.candidate && peer) {
          sendWs({ type: "call_ice", target_user_id: peer.id, candidate: e.candidate });
        }
      };

      pc.onconnectionstatechange = () => {
        if (["disconnected", "failed", "closed"].includes(pc.connectionState)) {
          setStatus("Call ended");
          setTimeout(() => onEnd(), 800);
        }
      };

      // Get local media
      const constraints = kind === "video"
        ? { audio: true, video: { width: 1280, height: 720 } }
        : { audio: true, video: false };
      let localStream;
      try {
        localStream = await navigator.mediaDevices.getUserMedia(constraints);
      } catch (err) {
        setMediaError(err?.message || "Permission denied");
        setStatus("No mic/camera access");
        return;
      }
      if (cancelled) {
        localStream.getTracks().forEach((t) => t.stop());
        return;
      }
      localStreamRef.current = localStream;
      if (localRef.current) localRef.current.srcObject = localStream;
      localStream.getTracks().forEach((t) => pc.addTrack(t, localStream));

      if (mode === "outgoing") {
        const o = await pc.createOffer();
        await pc.setLocalDescription(o);
        sendWs({ type: "call_offer", target_user_id: peer.id, kind, offer: o, peer: { id: me.id, name: me.name } });
      } else if (mode === "incoming" && offer) {
        await pc.setRemoteDescription(new RTCSessionDescription(offer));
        const a = await pc.createAnswer();
        await pc.setLocalDescription(a);
        sendWs({ type: "call_answer", target_user_id: from_user_id, answer: a });
        // flush any queued ice
        pendingIceRef.current.forEach((c) => pc.addIceCandidate(c).catch(() => {}));
        pendingIceRef.current = [];
      }
    };
    if (mode !== "incoming") setup();
    return () => {
      cancelled = true;
      try { pcRef.current?.close(); } catch (_) {}
      localStreamRef.current?.getTracks().forEach((t) => t.stop());
    };
    // eslint-disable-next-line
  }, [mode]);

  // Handle signaling events
  useEffect(() => {
    const handler = async (ev) => {
      const d = ev.detail;
      const pc = pcRef.current;
      if (!pc) return;
      if (d.type === "call_answer") {
        try { await pc.setRemoteDescription(new RTCSessionDescription(d.answer)); } catch (_) {}
      } else if (d.type === "call_ice") {
        const cand = new RTCIceCandidate(d.candidate);
        if (pc.remoteDescription) {
          try { await pc.addIceCandidate(cand); } catch (_) {}
        } else {
          pendingIceRef.current.push(cand);
        }
      }
    };
    window.addEventListener("call-signal", handler);
    return () => window.removeEventListener("call-signal", handler);
  }, []);

  const accept = () => {
    setStatus("Connecting…");
    onAccept();
  };

  const reject = () => {
    if (from_user_id) sendWs({ type: "call_reject", target_user_id: from_user_id });
    onEnd();
  };

  const toggleMute = () => {
    const tracks = localStreamRef.current?.getAudioTracks() || [];
    tracks.forEach((t) => (t.enabled = muted));
    setMuted(!muted);
  };
  const toggleCamera = () => {
    const tracks = localStreamRef.current?.getVideoTracks() || [];
    tracks.forEach((t) => (t.enabled = cameraOff));
    setCameraOff(!cameraOff);
  };

  // Incoming UI
  if (mode === "incoming") {
    return (
      <div className="fixed inset-0 z-50 bg-ink/85 backdrop-blur-xl flex flex-col items-center justify-center" data-testid="incoming-call-modal">
        <div className="text-sand/70 uppercase tracking-[0.3em] text-xs mb-6">Incoming {kind} call</div>
        <div className="relative">
          <Avatar name={peer?.name || "?"} size={140} />
          <div className="absolute inset-0 pulse-ring rounded-full" />
        </div>
        <div className="text-3xl text-sand font-heading mt-8">{peer?.name || "Unknown"}</div>
        <div className="flex items-center gap-6 mt-12">
          <button data-testid="reject-call-button" onClick={reject} className="w-16 h-16 rounded-full bg-terracotta text-sand flex items-center justify-center hover:scale-110 transition">
            <PhoneOff size={22} />
          </button>
          <button data-testid="accept-call-button" onClick={accept} className="w-16 h-16 rounded-full bg-sage text-sand flex items-center justify-center hover:scale-110 transition">
            <Phone size={22} />
          </button>
        </div>
      </div>
    );
  }

  // Active / outgoing UI
  return (
    <div className="fixed inset-0 z-50 bg-ink/95 backdrop-blur-xl flex flex-col p-6" data-testid="call-modal">
      <div className="flex items-center justify-between text-sand mb-4">
        <div>
          <div className="text-xs uppercase tracking-[0.3em] opacity-70">{kind} call</div>
          <div className="font-heading text-xl mt-1">{peer?.name}</div>
        </div>
        <div className="text-xs text-sand/70">{status}</div>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 min-h-0">
        {/* Remote video / avatar */}
        <div className="lg:col-span-2 relative bg-forest rounded-3xl overflow-hidden flex items-center justify-center">
          {mediaError ? (
            <div className="text-center p-8" data-testid="call-media-error">
              <div className="text-sand text-xl font-heading mb-2">Can't access mic/camera</div>
              <div className="text-sand/70 text-sm max-w-sm">{mediaError}. Please grant permission and try again.</div>
            </div>
          ) : kind === "video" ? (
            <video ref={remoteRef} autoPlay playsInline className="w-full h-full object-cover" data-testid="remote-video" />
          ) : (
            <div className="text-center">
              <Avatar name={peer?.name || "?"} size={160} />
              <div className="text-sand mt-6 font-heading text-2xl">{peer?.name}</div>
            </div>
          )}
        </div>
        {/* Local video */}
        <div className="bg-ink rounded-3xl overflow-hidden flex items-center justify-center border border-white/10 relative aspect-video lg:aspect-auto">
          {kind === "video" && !cameraOff ? (
            <video ref={localRef} autoPlay muted playsInline className="w-full h-full object-cover" data-testid="local-video" />
          ) : (
            <Avatar name={me.name} size={120} />
          )}
          <div className="absolute bottom-3 left-3 text-xs text-sand/80 bg-black/40 px-2 py-1 rounded-full">You</div>
        </div>
      </div>

      {/* Controls */}
      <div className="flex justify-center mt-6">
        <div className="flex gap-3 bg-ink/80 p-3 rounded-full backdrop-blur-md border border-white/10">
          <button
            data-testid="toggle-mute-button"
            onClick={toggleMute}
            className={`w-12 h-12 rounded-full flex items-center justify-center transition ${muted ? "bg-terracotta text-sand" : "bg-white/10 text-sand hover:bg-white/20"}`}
          >
            {muted ? <MicOff size={18} /> : <Mic size={18} />}
          </button>
          {kind === "video" && (
            <button
              data-testid="toggle-camera-button"
              onClick={toggleCamera}
              className={`w-12 h-12 rounded-full flex items-center justify-center transition ${cameraOff ? "bg-terracotta text-sand" : "bg-white/10 text-sand hover:bg-white/20"}`}
            >
              {cameraOff ? <VideoOff size={18} /> : <Video size={18} />}
            </button>
          )}
          <button
            data-testid="end-call-button"
            onClick={onEnd}
            className="w-12 h-12 rounded-full bg-terracotta text-sand flex items-center justify-center hover:bg-terracottaHover transition"
          >
            <PhoneOff size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
