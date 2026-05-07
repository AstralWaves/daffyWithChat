import React, { useState } from "react";
import { X, Camera } from "lucide-react";
import { api, formatErr } from "../api";
import { Avatar } from "./Sidebar";

export default function ProfileModal({ user, onClose, onUpdated }) {
  const [name, setName] = useState(user.name || "");
  const [bio, setBio] = useState(user.bio || "");
  const [avatar, setAvatar] = useState(user.avatar || null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const onFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 2 * 1024 * 1024) { setError("Avatar must be under 2MB"); return; }
    const reader = new FileReader();
    reader.onload = () => setAvatar(reader.result);
    reader.readAsDataURL(f);
  };

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      const { data } = await api.patch("/users/me", { name, bio, avatar });
      onUpdated(data);
      onClose();
    } catch (e) {
      setError(formatErr(e.response?.data?.detail) || e.message);
    }
    setSaving(false);
  };

  return (
    <div className="fixed inset-0 z-40 bg-ink/40 backdrop-blur-sm flex items-center justify-center p-4" data-testid="profile-modal">
      <div className="bg-sand rounded-3xl w-full max-w-md p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-heading font-medium">Your profile</h3>
          <button onClick={onClose} data-testid="close-profile-modal" className="p-2 hover:bg-bordr rounded-full">
            <X size={18} />
          </button>
        </div>

        <div className="flex flex-col items-center mb-6">
          <label className="relative cursor-pointer group">
            <Avatar name={name || user.username} src={avatar} size={96} />
            <div className="absolute inset-0 rounded-full bg-ink/0 group-hover:bg-ink/40 transition flex items-center justify-center">
              <Camera size={20} className="text-white opacity-0 group-hover:opacity-100 transition" />
            </div>
            <input type="file" accept="image/*" className="hidden" onChange={onFile} data-testid="avatar-upload-input" />
          </label>
          <div className="text-xs text-muted mt-3">@{user.username}</div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs uppercase tracking-[0.2em] font-semibold text-muted">Display name</label>
            <input
              data-testid="profile-name-input"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-2 w-full bg-white border border-bordr rounded-xl px-4 py-3 focus:ring-2 focus:ring-terracotta/30 focus:border-terracotta"
            />
          </div>
          <div>
            <label className="text-xs uppercase tracking-[0.2em] font-semibold text-muted">Bio</label>
            <textarea
              data-testid="profile-bio-input"
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              rows={3}
              placeholder="A line or two about you…"
              className="mt-2 w-full bg-white border border-bordr rounded-xl px-4 py-3 focus:ring-2 focus:ring-terracotta/30 focus:border-terracotta resize-none"
            />
          </div>
        </div>

        {error && <div className="mt-3 text-sm text-terracotta">{error}</div>}

        <button
          data-testid="save-profile-button"
          onClick={save}
          disabled={saving}
          className="mt-6 w-full bg-forest text-sand rounded-full py-3 font-medium hover:bg-ink transition disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save changes"}
        </button>
      </div>
    </div>
  );
}
