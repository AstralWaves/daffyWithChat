import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";

const BG_IMG =
  "https://images.unsplash.com/photo-1712280473267-28c10230e95c?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzl8MHwxfHNlYXJjaHwxfHxhYnN0cmFjdCUyMGFyY2hpdGVjdHVyYWwlMjBuZXV0cmFsJTIwdGVycmFjb3R0YSUyMGJhY2tncm91bmR8ZW58MHx8fHwxNzc4MTg2ODk5fDA&ixlib=rb-4.1.0&q=85";

export default function AuthScreen({ mode }) {
  const isLogin = mode === "login";
  const navigate = useNavigate();
  const { login, register } = useAuth();
  const [form, setForm] = useState({ email: "", password: "", username: "", name: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    const res = isLogin
      ? await login(form.email, form.password)
      : await register({ email: form.email, password: form.password, username: form.username, name: form.name });
    setLoading(false);
    if (res.ok) navigate("/");
    else setError(res.error || "Failed");
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-sand">
      {/* Left form */}
      <div className="flex items-center justify-center p-8 lg:p-16">
        <div className="w-full max-w-md">
          <div className="mb-12">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-2.5 h-2.5 rounded-full bg-terracotta" />
              <span className="text-xs uppercase tracking-[0.25em] text-muted font-semibold">Ember</span>
            </div>
            <h1 className="text-5xl font-medium text-ink mt-6 leading-[1.05]">
              {isLogin ? <>Welcome<br/>back.</> : <>Start a<br/>conversation.</>}
            </h1>
            <p className="text-muted mt-4 text-base leading-relaxed">
              {isLogin
                ? "Sign in to keep the thread going. Real-time, end-to-end."
                : "Create an account to chat, call, and connect with anyone."}
            </p>
          </div>

          <form onSubmit={submit} className="space-y-4" data-testid={`${mode}-form`}>
            {!isLogin && (
              <>
                <div>
                  <label className="text-xs uppercase tracking-[0.2em] font-semibold text-muted">Username</label>
                  <input
                    data-testid="register-username-input"
                    type="text"
                    required
                    value={form.username}
                    onChange={(e) => setForm({ ...form, username: e.target.value })}
                    placeholder="ada_lovelace"
                    className="mt-2 w-full bg-white border border-bordr rounded-xl px-4 py-3 focus:ring-2 focus:ring-terracotta/30 focus:border-terracotta transition"
                  />
                </div>
                <div>
                  <label className="text-xs uppercase tracking-[0.2em] font-semibold text-muted">Display name</label>
                  <input
                    data-testid="register-name-input"
                    type="text"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="Ada Lovelace"
                    className="mt-2 w-full bg-white border border-bordr rounded-xl px-4 py-3 focus:ring-2 focus:ring-terracotta/30 focus:border-terracotta transition"
                  />
                </div>
              </>
            )}
            <div>
              <label className="text-xs uppercase tracking-[0.2em] font-semibold text-muted">Email</label>
              <input
                data-testid={`${mode}-email-input`}
                type="email"
                required
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="you@somewhere.com"
                className="mt-2 w-full bg-white border border-bordr rounded-xl px-4 py-3 focus:ring-2 focus:ring-terracotta/30 focus:border-terracotta transition"
              />
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.2em] font-semibold text-muted">Password</label>
              <input
                data-testid={`${mode}-password-input`}
                type="password"
                required
                minLength={6}
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="••••••••"
                className="mt-2 w-full bg-white border border-bordr rounded-xl px-4 py-3 focus:ring-2 focus:ring-terracotta/30 focus:border-terracotta transition"
              />
            </div>

            {error && (
              <div data-testid="auth-error" className="text-sm text-terracotta bg-terracotta/10 border border-terracotta/30 rounded-xl p-3">
                {error}
              </div>
            )}

            <button
              data-testid={`${mode}-submit-button`}
              type="submit"
              disabled={loading}
              className="w-full bg-forest text-sand rounded-full py-3.5 font-medium tracking-wide hover:bg-ink transition-all duration-300 disabled:opacity-50"
            >
              {loading ? "Please wait…" : isLogin ? "Sign in" : "Create account"}
            </button>
          </form>

          <div className="mt-8 text-sm text-muted">
            {isLogin ? (
              <>
                New here?{" "}
                <Link to="/register" data-testid="goto-register-link" className="text-terracotta font-semibold hover:underline">
                  Create an account
                </Link>
              </>
            ) : (
              <>
                Already have one?{" "}
                <Link to="/login" data-testid="goto-login-link" className="text-terracotta font-semibold hover:underline">
                  Sign in
                </Link>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Right image */}
      <div className="hidden lg:block relative overflow-hidden">
        <img src={BG_IMG} alt="" className="w-full h-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-tr from-terracotta/30 via-transparent to-forest/20" />
        <div className="absolute bottom-12 left-12 right-12 text-sand">
          <div className="text-xs uppercase tracking-[0.3em] mb-3 opacity-80">Live · Encrypted · Calm</div>
          <div className="text-3xl font-medium leading-tight font-heading">
            Conversations, beautifully<br />unhurried.
          </div>
        </div>
      </div>
    </div>
  );
}
