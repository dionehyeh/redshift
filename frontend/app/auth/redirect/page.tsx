"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { UserProfile } from "@/lib/types";
import { Loader2, Sprout } from "lucide-react";

export default function AuthRedirectPage() {
  const router = useRouter();
  const [statusText, setStatusText] = useState("Loading your account…");

  useEffect(() => {
    let active = true;
    async function redirectUser() {
      try {
        const user = await api<UserProfile>("/me");
        if (active) {
          router.replace(
            user.role === "mentor" || user.role === "officer"
              ? "/inbox"
              : "/fields"
          );
        }
      } catch {
        if (active) {
          setStatusText("Redirecting to dashboard…");
          router.replace("/fields");
        }
      }
    }
    void redirectUser();
    return () => { active = false; };
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center p-4 bg-gradient-to-br from-green-950 via-stone-900 to-stone-800">
      <div className="bg-white rounded-3xl p-10 text-center max-w-xs w-full shadow-2xl space-y-5">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-emerald-500 to-green-700 flex items-center justify-center shadow-lg">
          <Sprout className="w-8 h-8 text-white" />
        </div>
        <Loader2 className="w-7 h-7 animate-spin text-emerald-600 mx-auto" />
        <p className="text-sm font-semibold text-stone-600">{statusText}</p>
      </div>
    </main>
  );
}
