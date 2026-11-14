"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { UserProfile } from "@/lib/types";

export default function AuthRedirectPage() {
  const router = useRouter();
  const [error, setError] = useState("");

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
      } catch (requestError) {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Unable to load your account profile"
          );
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
      <div className="rounded-xl bg-white p-6 text-center shadow-sm">
        {error ? (
          <p className="text-sm text-red-700">{error}</p>
        ) : (
          <p className="text-sm text-slate-600">Loading your account...</p>
        )}
      </div>
    </main>
  );
}
