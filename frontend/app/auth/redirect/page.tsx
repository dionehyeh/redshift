"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { UserProfile } from "@/lib/types";
import { Loader2 } from "lucide-react";

export default function AuthRedirectPage() {
  const router = useRouter();
  const [statusText, setStatusText] = useState("Loading your account...");

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
        // If backend /me is not reachable, gracefully fallback to the primary /fields view
        if (active) {
          setStatusText("Redirecting to plots dashboard...");
          router.replace("/fields");
        }
      }
    }

    void redirectUser();
    return () => {
      active = false;
    };
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
      <div className="rounded-2xl bg-white p-8 text-center shadow-sm max-w-sm w-full space-y-3">
        <Loader2 className="w-6 h-6 animate-spin text-emerald-700 mx-auto" />
        <p className="text-sm font-medium text-slate-700">{statusText}</p>
      </div>
    </main>
  );
}
