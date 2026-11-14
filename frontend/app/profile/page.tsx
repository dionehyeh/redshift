"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

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
    <section className="mx-auto max-w-2xl space-y-6">
      <header className="space-y-2">
        <Link href="/" className="text-sm font-medium text-emerald-700 hover:underline">
          Back to Field Shift
        </Link>
        <h1 className="text-2xl font-bold text-slate-900">Account profile</h1>
        <p className="text-sm text-slate-600">
          Your sign-in is managed by Clerk. Update your Field Shift preferences here.
        </p>
      </header>

      {loading ? (
        <p className="rounded-xl border border-slate-200 bg-white p-5 text-sm text-slate-600">
          Loading your profile...
        </p>
      ) : error && !profile ? (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
        >
          {error}
        </div>
      ) : profile ? (
        <>
          <dl className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Name
              </dt>
              <dd className="mt-1 text-sm font-medium text-slate-900">
                {profile.name}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Email or phone
              </dt>
              <dd className="mt-1 break-all text-sm font-medium text-slate-900">
                {profile.contact}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Account type
              </dt>
              <dd className="mt-1 text-sm font-medium capitalize text-slate-900">
                {profile.helper_type
                  ? `${profile.role} · ${profile.helper_type}`
                  : profile.role}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Field Shift ID
              </dt>
              <dd className="mt-1 text-sm font-medium text-slate-900">
                {profile.id}
              </dd>
            </div>
          </dl>

          <form
            onSubmit={savePreferences}
            className="space-y-5 rounded-2xl border border-slate-200 bg-white p-5"
          >
            <h2 className="text-lg font-semibold text-slate-900">Preferences</h2>

            <label className="block space-y-1">
              <span className="text-sm font-medium text-slate-700">Language</span>
              <select
                value={language}
                onChange={(event) =>
                  setLanguage(event.target.value === "ml" ? "ml" : "en")
                }
                className="h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
              >
                <option value="en">English</option>
                <option value="ml">Malayalam</option>
              </select>
            </label>

            <label className="block space-y-1">
              <span className="text-sm font-medium text-slate-700">
                Planning preference
              </span>
              <select
                value={marketToggle ?? ""}
                onChange={(event) => {
                  const value = event.target.value;
                  setMarketToggle(
                    value === "earn_more" || value === "play_safe" ? value : null
                  );
                }}
                className="h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
              >
                <option value="">No default preference</option>
                <option value="earn_more">Earn more</option>
                <option value="play_safe">Play safe</option>
              </select>
            </label>

            <label className="flex items-start gap-3 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={shareConsent === 1}
                onChange={(event) =>
                  setShareConsent(event.target.checked ? 1 : 0)
                }
                className="mt-1 h-4 w-4 rounded border-slate-300 text-emerald-700"
              />
              <span>
                Use my default sharing consent when preparing reports. You can
                still review and change the fields shared on each report.
              </span>
            </label>

            {error && (
              <p role="alert" className="text-sm text-red-700">
                {error}
              </p>
            )}
            {saved && (
              <p role="status" className="text-sm text-emerald-700">
                Preferences saved.
              </p>
            )}

            <button
              type="submit"
              disabled={saving}
              className="h-11 rounded-xl bg-emerald-700 px-5 text-sm font-medium text-white hover:bg-emerald-800 disabled:opacity-60"
            >
              {saving ? "Saving..." : "Save preferences"}
            </button>
          </form>
        </>
      ) : null}
    </section>
  );
}
