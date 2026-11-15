"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";
import type { UserPrefsUpdate, UserProfile } from "@/lib/types";

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [language, setLanguage] = useState<UserProfile["language"]>("en");
  const [marketToggle, setMarketToggle] =
    useState<UserProfile["market_toggle"]>(null);
  const [shareConsent, setShareConsent] = useState<0 | 1>(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let active = true;

    async function loadProfile() {
      try {
        const user = await api<UserProfile>("/me");
        if (active) {
          setProfile(user);
          setLanguage(user.language);
          setMarketToggle(user.market_toggle);
          setShareConsent(user.default_share_consent);
        }
      } catch (requestError) {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Unable to load your profile"
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadProfile();
    return () => {
      active = false;
    };
  }, []);

  async function savePreferences(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setSaved(false);
    setError("");

    const changes: UserPrefsUpdate = {
      language,
      market_toggle: marketToggle,
      default_share_consent: shareConsent,
    };

    try {
      const updatedProfile = await api<UserProfile>("/me/prefs", {
        method: "PATCH",
        body: JSON.stringify(changes),
      });
      setProfile(updatedProfile);
      setLanguage(updatedProfile.language);
      setMarketToggle(updatedProfile.market_toggle);
      setShareConsent(updatedProfile.default_share_consent);
      setSaved(true);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to save your preferences"
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-stone-50 via-stone-100 to-amber-50">
      {/* ── Top bar ── */}
      <div className="sticky top-0 z-40 bg-gradient-to-r from-green-900 via-green-800 to-emerald-900 shadow-lg">
        <div className="max-w-4xl mx-auto flex items-center justify-between px-5 h-14">
          <Link
            href="/fields"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white/15 text-white text-sm font-semibold hover:bg-white/25 transition-all"
          >
            <ArrowLeft className="w-4 h-4" />
            My Fields
          </Link>
          <span className="text-emerald-200/70 text-xs font-bold tracking-widest uppercase">
            Field Shift
          </span>
        </div>
      </div>

      {/* ── Content ── */}
      <section className="mx-auto max-w-2xl space-y-6 px-5 py-10">
        <header className="space-y-2">
          <h1 className="text-3xl font-extrabold text-stone-900">
            Account Profile
          </h1>
          <p className="text-sm text-stone-500">
            Your sign-in is managed by Clerk. Update your Field Shift
            preferences here.
          </p>
        </header>

        {loading ? (
          <div className="rounded-2xl border-2 border-stone-200 bg-white p-8 text-center">
            <div className="w-8 h-8 border-4 border-stone-200 border-t-green-700 rounded-full animate-spin mx-auto" />
            <p className="text-sm text-stone-500 mt-3">Loading profile…</p>
          </div>
        ) : error && !profile ? (
          <div
            role="alert"
            className="rounded-2xl border-2 border-red-200 bg-red-50 p-5 text-sm text-red-800 font-medium"
          >
            {error}
          </div>
        ) : profile ? (
          <>
            {/* Profile info card */}
            <dl className="grid gap-4 rounded-2xl border-2 border-stone-200 bg-white p-6 sm:grid-cols-2">
              {[
                { label: "Name", value: profile.name },
                { label: "Email or phone", value: profile.contact },
                {
                  label: "Account type",
                  value: profile.helper_type
                    ? `${profile.role} · ${profile.helper_type}`
                    : profile.role,
                },
                { label: "Field Shift ID", value: String(profile.id) },
              ].map((item) => (
                <div key={item.label}>
                  <dt className="text-[10px] font-bold uppercase tracking-widest text-stone-400">
                    {item.label}
                  </dt>
                  <dd className="mt-1 text-sm font-semibold text-stone-800 capitalize">
                    {item.value}
                  </dd>
                </div>
              ))}
            </dl>

            {/* Preferences form */}
            <form
              onSubmit={savePreferences}
              className="space-y-5 rounded-2xl border-2 border-stone-200 bg-white p-6"
            >
              <h2 className="text-lg font-extrabold text-stone-900">
                Preferences
              </h2>

              <label className="block space-y-1.5">
                <span className="text-sm font-semibold text-stone-700">
                  Language
                </span>
                <select
                  value={language}
                  onChange={(event) =>
                    setLanguage(event.target.value === "ml" ? "ml" : "en")
                  }
                  className="h-12 w-full rounded-xl border-2 border-stone-200 bg-stone-50 px-4 text-sm font-medium focus:border-green-600 focus:ring-2 focus:ring-green-600/20 outline-none transition"
                >
                  <option value="en">English</option>
                  <option value="ml">Malayalam</option>
                </select>
              </label>

              <label className="block space-y-1.5">
                <span className="text-sm font-semibold text-stone-700">
                  Planning preference
                </span>
                <select
                  value={marketToggle ?? ""}
                  onChange={(event) => {
                    const value = event.target.value;
                    setMarketToggle(
                      value === "earn_more" || value === "play_safe"
                        ? value
                        : null
                    );
                  }}
                  className="h-12 w-full rounded-xl border-2 border-stone-200 bg-stone-50 px-4 text-sm font-medium focus:border-green-600 focus:ring-2 focus:ring-green-600/20 outline-none transition"
                >
                  <option value="">No default preference</option>
                  <option value="earn_more">Earn more</option>
                  <option value="play_safe">Play safe</option>
                </select>
              </label>

              <label className="flex items-start gap-3 text-sm text-stone-700 bg-stone-50 p-4 rounded-xl border border-stone-200">
                <input
                  type="checkbox"
                  checked={shareConsent === 1}
                  onChange={(event) =>
                    setShareConsent(event.target.checked ? 1 : 0)
                  }
                  className="mt-0.5 h-5 w-5 rounded border-stone-300 text-green-700 focus:ring-green-600"
                />
                <span>
                  Use my default sharing consent when preparing reports. You can
                  still review and change the fields shared on each report.
                </span>
              </label>

              {error && (
                <div
                  role="alert"
                  className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl px-4 py-3 font-medium"
                >
                  {error}
                </div>
              )}
              {saved && (
                <div
                  role="status"
                  className="text-sm text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3 font-medium"
                >
                  ✅ Preferences saved successfully.
                </div>
              )}

              <button
                type="submit"
                disabled={saving}
                className="h-12 w-full rounded-xl bg-gradient-to-r from-green-700 to-emerald-700 px-6 text-sm font-bold text-white shadow-md hover:shadow-lg hover:from-green-800 hover:to-emerald-800 disabled:opacity-60 transition-all"
              >
                {saving ? "Saving…" : "Save Preferences"}
              </button>
            </form>
          </>
        ) : null}
      </section>
    </div>
  );
}
