"use client";

import { SignUp } from "@clerk/nextjs";
import { Sprout } from "lucide-react";

export default function RegisterPage() {
  return (
    <main className="flex min-h-screen items-center justify-center p-4 bg-gradient-to-br from-green-950 via-stone-900 to-stone-800 relative overflow-hidden">
      <div className="absolute top-10 right-10 w-72 h-72 bg-emerald-500/10 rounded-full blur-3xl" />
      <div className="absolute bottom-10 left-10 w-80 h-80 bg-amber-500/10 rounded-full blur-3xl" />

      <div className="relative z-10 flex flex-col items-center gap-8">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-emerald-500 to-green-700 flex items-center justify-center shadow-xl shadow-emerald-500/30">
            <Sprout className="w-7 h-7 text-white" />
          </div>
          <div>
            <div className="text-white font-black text-2xl tracking-tight">
              Field Shift
            </div>
            <div className="text-emerald-400/60 text-[10px] font-bold uppercase tracking-[0.2em]">
              NASA Earth Data
            </div>
          </div>
        </div>

        <SignUp
          routing="path"
          path="/register"
          signInUrl="/login"
          forceRedirectUrl="/auth/redirect"
        />
      </div>
    </main>
  );
}
