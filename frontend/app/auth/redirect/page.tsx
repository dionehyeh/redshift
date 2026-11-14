"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type UserProfile = {
  role: string;
};

export default function AuthRedirectPage() {
  const router = useRouter();
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function redirectUser() {
      try {
        const response = await fetch("/api/me", { cache: "no-store" });
        if (
          !response.ok ||
          !response.headers.get("content-type")?.includes("application/json")
        ) {
          throw new Error("Unable to load your account profile");
        }

        const user = (await response.json()) as UserProfile;
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
