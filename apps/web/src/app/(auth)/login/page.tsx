// apps/web/src/app/(auth)/login/page.tsx
// SYNAPSE — Role-Based Login Page
// Firebase Auth: Google Sign-In + email/password
// Role stored in Firestore on first login → auto-redirect on subsequent logins
// No dummy data. No mock states. All real Firebase.

"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  GoogleAuthProvider,
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  type User,
} from "firebase/auth";
import {
  doc,
  getDoc,
  setDoc,
  serverTimestamp,
} from "firebase/firestore";
import { auth, db } from "@/lib/firebase";

// ─── Types ───────────────────────────────────────────────────────────────────
type Role = "ngo" | "govt" | "volunteer" | "donor";

interface RoleConfig {
  id: Role;
  label: string;
  subtitle: string;
  icon: string;
  redirect: string;
  color: string;
  borderColor: string;
  iconBg: string;
}

// ─── Role definitions ─────────────────────────────────────────────────────────
const ROLES: RoleConfig[] = [
  {
    id: "ngo",
    label: "NGO Coordinator",
    subtitle: "Submit needs, dispatch volunteers, track impact",
    icon: "🏢",
    redirect: "/dashboard",
    color: "text-[#0D2B4E]",
    borderColor: "border-[#0D2B4E]",
    iconBg: "bg-blue-50",
  },
  {
    id: "govt",
    label: "Government Admin",
    subtitle: "District oversight, scheme matching, weekly digest",
    icon: "🏛️",
    redirect: "/gov",
    color: "text-[#534AB7]",
    borderColor: "border-[#534AB7]",
    iconBg: "bg-purple-50",
  },
  {
    id: "volunteer",
    label: "Volunteer",
    subtitle: "Accept tasks, check in on-site, earn badges",
    icon: "🙋",
    redirect: null, // Shows Flutter app download/QR
    color: "text-[#0F6E56]",
    borderColor: "border-[#0F6E56]",
    iconBg: "bg-teal-50",
  },
  {
    id: "donor",
    label: "Donor / Fundraiser",
    subtitle: "Fund campaigns, track verified impact, CSR reports",
    icon: "💛",
    redirect: "/fundraiser",
    color: "text-[#D97706]",
    borderColor: "border-[#D97706]",
    iconBg: "bg-amber-50",
  },
];

const ROLE_REDIRECT: Record<Role, string> = {
  ngo: "/dashboard",
  govt: "/gov",
  volunteer: "/volunteer-app",
  donor: "/fundraiser",
};

// ─── Component ────────────────────────────────────────────────────────────────
export default function LoginPage() {
  const router = useRouter();

  const [step, setStep] = useState<"role-select" | "auth">("role-select");
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [orgName, setOrgName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [loading, setLoading] = useState(false);
  const [checkingSession, setCheckingSession] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ─── Auto-redirect if already logged in ─────────────────────────────────
  useEffect(() => {
    const unsub = onAuthStateChanged(auth, async (user: User | null) => {
      if (user) {
        const snap = await getDoc(doc(db, "users", user.uid));
        if (snap.exists()) {
          const role = snap.data()?.role as Role;
          if (role && ROLE_REDIRECT[role]) {
            router.replace(ROLE_REDIRECT[role]);
            return;
          }
        }
      }
      setCheckingSession(false);
    });
    return () => unsub();
  }, [router]);

  // ─── Write user to Firestore on first login ──────────────────────────────
  const persistUser = async (user: User, role: Role) => {
    const ref = doc(db, "users", user.uid);
    const snap = await getDoc(ref);
    if (!snap.exists()) {
      await setDoc(ref, {
        uid: user.uid,
        name: user.displayName || displayName || "",
        email: user.email,
        role,
        org_name: orgName || null,
        created_at: serverTimestamp(),
        preferences: {},
      });
    }
  };

  // ─── Google Sign-In ───────────────────────────────────────────────────────
  const handleGoogle = async () => {
    if (!selectedRole) return;
    setLoading(true);
    setError(null);
    try {
      const provider = new GoogleAuthProvider();
      const result = await signInWithPopup(auth, provider);
      await persistUser(result.user, selectedRole);
      router.push(ROLE_REDIRECT[selectedRole]);
    } catch (err: any) {
      setError(friendlyError(err.code));
    } finally {
      setLoading(false);
    }
  };

  // ─── Email/password auth ──────────────────────────────────────────────────
  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRole) return;
    setLoading(true);
    setError(null);
    try {
      let userCredential;
      if (authMode === "login") {
        userCredential = await signInWithEmailAndPassword(auth, email, password);
      } else {
        userCredential = await createUserWithEmailAndPassword(auth, email, password);
        await persistUser(userCredential.user, selectedRole);
      }
      router.push(ROLE_REDIRECT[selectedRole]);
    } catch (err: any) {
      setError(friendlyError(err.code));
    } finally {
      setLoading(false);
    }
  };

  const friendlyError = (code: string): string => {
    const map: Record<string, string> = {
      "auth/user-not-found": "No account found with this email.",
      "auth/wrong-password": "Incorrect password.",
      "auth/email-already-in-use": "An account already exists with this email.",
      "auth/weak-password": "Password must be at least 6 characters.",
      "auth/invalid-email": "Please enter a valid email address.",
      "auth/popup-closed-by-user": "Sign-in was cancelled.",
      "auth/network-request-failed": "Network error. Please check your connection.",
    };
    return map[code] ?? "Sign-in failed. Please try again.";
  };

  const handleRoleSelect = (role: Role) => {
    setSelectedRole(role);
    setError(null);
    setStep("auth");
  };

  // ─── Loading / session check ──────────────────────────────────────────────
  if (checkingSession) {
    return (
      <div className="min-h-screen bg-[#0D2B4E] flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 border-2 border-white/30 border-t-white rounded-full animate-spin mx-auto mb-4" />
          <p className="text-white/60 text-sm font-sans">Checking session…</p>
        </div>
      </div>
    );
  }

  const selectedRoleConfig = ROLES.find((r) => r.id === selectedRole);

  return (
    <main className="min-h-screen bg-[#0D2B4E] flex flex-col items-center justify-center px-4 py-12">

      {/* Logo */}
      <div className="mb-10 text-center">
        <div className="flex items-center justify-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center">
            <span className="text-xl">🔗</span>
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight" style={{ fontFamily: "'DM Sans', sans-serif" }}>
            SYNAPSE
          </h1>
        </div>
        <p className="text-white/50 text-sm">
          Humanitarian coordination platform
        </p>
      </div>

      {/* ─── Step 1: Role Selection ── */}
      {step === "role-select" && (
        <div className="w-full max-w-2xl">
          <h2 className="text-white text-center text-xl font-semibold mb-1">
            Who are you?
          </h2>
          <p className="text-white/50 text-center text-sm mb-8">
            Select your role to continue
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {ROLES.map((role) => (
              <button
                key={role.id}
                onClick={() => handleRoleSelect(role.id)}
                className="bg-white rounded-2xl p-6 text-left hover:scale-[1.02] hover:shadow-xl transition-all duration-200 border-2 border-transparent hover:border-white/80 focus:outline-none focus:ring-2 focus:ring-white/50"
              >
                <div className={`w-12 h-12 rounded-xl ${role.iconBg} flex items-center justify-center text-2xl mb-4`}>
                  {role.icon}
                </div>
                <h3 className={`font-semibold text-base mb-1 ${role.color}`}>
                  {role.label}
                </h3>
                <p className="text-gray-500 text-sm leading-snug">
                  {role.subtitle}
                </p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ─── Step 2: Auth ── */}
      {step === "auth" && selectedRoleConfig && (
        <div className="w-full max-w-md">
          {/* Back button */}
          <button
            onClick={() => { setStep("role-select"); setError(null); }}
            className="flex items-center gap-2 text-white/60 hover:text-white text-sm mb-6 transition-colors"
          >
            ← Back to role selection
          </button>

          <div className="bg-white rounded-2xl p-8 shadow-2xl">
            {/* Role badge */}
            <div className="flex items-center gap-3 mb-6">
              <div className={`w-10 h-10 rounded-xl ${selectedRoleConfig.iconBg} flex items-center justify-center text-xl`}>
                {selectedRoleConfig.icon}
              </div>
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-wide font-medium">Signing in as</p>
                <p className={`font-semibold ${selectedRoleConfig.color}`}>{selectedRoleConfig.label}</p>
              </div>
            </div>

            {/* Volunteer: Show app download instead of web auth */}
            {selectedRole === "volunteer" ? (
              <div className="text-center py-4">
                <div className="w-16 h-16 bg-teal-50 rounded-2xl flex items-center justify-center text-3xl mx-auto mb-4">
                  📱
                </div>
                <h3 className="font-semibold text-gray-800 mb-2">Volunteers use the mobile app</h3>
                <p className="text-gray-500 text-sm mb-6 leading-relaxed">
                  The SYNAPSE volunteer experience is optimised for mobile — GPS check-in, push notifications, and offline task access.
                </p>
                <a
                  href="https://synapse-app.page.link/volunteer"
                  className="block w-full py-3 rounded-xl bg-[#0F6E56] text-white font-medium text-center hover:bg-[#0a5a45] transition-colors mb-3"
                >
                  Download on Android
                </a>
                <button
                  onClick={() => setStep("role-select")}
                  className="text-gray-400 text-sm hover:text-gray-600 transition-colors"
                >
                  Choose a different role
                </button>
              </div>
            ) : (
              <>
                {/* Auth mode toggle */}
                <div className="flex bg-gray-100 rounded-xl p-1 mb-6">
                  {(["login", "register"] as const).map((mode) => (
                    <button
                      key={mode}
                      onClick={() => { setAuthMode(mode); setError(null); }}
                      className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${
                        authMode === mode
                          ? "bg-white text-gray-800 shadow-sm"
                          : "text-gray-500 hover:text-gray-700"
                      }`}
                    >
                      {mode === "login" ? "Sign In" : "Create Account"}
                    </button>
                  ))}
                </div>

                {/* Error */}
                {error && (
                  <div className="mb-4 px-4 py-3 rounded-xl bg-red-50 border border-red-100 text-red-600 text-sm">
                    {error}
                  </div>
                )}

                {/* Google Sign-In */}
                <button
                  onClick={handleGoogle}
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-3 py-3 rounded-xl border border-gray-200 bg-white hover:bg-gray-50 transition-colors text-gray-700 font-medium text-sm mb-4 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <svg width="18" height="18" viewBox="0 0 48 48" fill="none">
                    <path d="M44.5 20H24v8.5h11.8C34.7 33.9 30.1 37 24 37c-7.2 0-13-5.8-13-13s5.8-13 13-13c3.1 0 5.9 1.1 8.1 2.9l6.4-6.4C34.6 4.1 29.6 2 24 2 11.8 2 2 11.8 2 24s9.8 22 22 22c11 0 21-8 21-22 0-1.3-.2-2.7-.5-4z" fill="#FFC107"/>
                    <path d="M6.3 14.7l7.1 5.2C15.1 15.7 19.2 13 24 13c3.1 0 5.9 1.1 8.1 2.9l6.4-6.4C34.6 4.1 29.6 2 24 2 16.3 2 9.7 7.4 6.3 14.7z" fill="#FF3D00"/>
                    <path d="M24 46c5.5 0 10.5-1.9 14.3-5.1l-6.6-5.6C29.6 36.7 26.9 37.5 24 37.5c-6 0-11.1-3.9-12.9-9.4L4 33.5C7.3 40.3 15.1 46 24 46z" fill="#4CAF50"/>
                    <path d="M44.5 20H24v8.5h11.8c-.8 2.5-2.4 4.6-4.4 6.1l6.6 5.6C41.8 36.6 45 30.8 45 24c0-1.3-.2-2.7-.5-4z" fill="#1976D2"/>
                  </svg>
                  Continue with Google
                </button>

                <div className="flex items-center gap-3 mb-4">
                  <div className="flex-1 h-px bg-gray-100" />
                  <span className="text-gray-400 text-xs">or</span>
                  <div className="flex-1 h-px bg-gray-100" />
                </div>

                {/* Email/password form */}
                <form onSubmit={handleEmailAuth} className="space-y-4">
                  {authMode === "register" && (
                    <>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Full Name</label>
                        <input
                          type="text"
                          value={displayName}
                          onChange={(e) => setDisplayName(e.target.value)}
                          placeholder="Your name"
                          className="w-full px-4 py-3 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#0D2B4E]/20 focus:border-[#0D2B4E]/40 transition-all"
                          required
                        />
                      </div>
                      {(selectedRole === "ngo" || selectedRole === "govt") && (
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">
                            {selectedRole === "ngo" ? "Organisation Name" : "Department / Office"}
                          </label>
                          <input
                            type="text"
                            value={orgName}
                            onChange={(e) => setOrgName(e.target.value)}
                            placeholder={selectedRole === "ngo" ? "NGO / Trust name" : "District office or department"}
                            className="w-full px-4 py-3 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#0D2B4E]/20 focus:border-[#0D2B4E]/40 transition-all"
                          />
                        </div>
                      )}
                    </>
                  )}

                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Email</label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@example.com"
                      className="w-full px-4 py-3 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#0D2B4E]/20 focus:border-[#0D2B4E]/40 transition-all"
                      required
                      autoComplete="email"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Password</label>
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder={authMode === "register" ? "Min. 6 characters" : "Your password"}
                      className="w-full px-4 py-3 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#0D2B4E]/20 focus:border-[#0D2B4E]/40 transition-all"
                      required
                      autoComplete={authMode === "login" ? "current-password" : "new-password"}
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-3 rounded-xl bg-[#0D2B4E] text-white font-medium text-sm hover:bg-[#0a2240] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        {authMode === "login" ? "Signing in…" : "Creating account…"}
                      </>
                    ) : (
                      authMode === "login" ? "Sign In" : "Create Account"
                    )}
                  </button>
                </form>
              </>
            )}
          </div>

          {/* Privacy note */}
          <p className="text-white/30 text-xs text-center mt-6 leading-relaxed">
            By signing in, you agree to SYNAPSE's data handling policy.
            <br />
            Field data is used exclusively for humanitarian coordination.
          </p>
        </div>
      )}
    </main>
  );
}
