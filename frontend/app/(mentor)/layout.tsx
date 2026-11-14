import Link from "next/link";
import { UserButton } from "@clerk/nextjs";
import { GraduationCap, Inbox, User } from "lucide-react";

export default function MentorLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-b from-stone-50 via-stone-100 to-amber-50">
      <header className="sticky top-0 z-50 bg-gradient-to-r from-stone-800 via-stone-900 to-stone-800 shadow-lg">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-5 h-16">
          <Link href="/inbox" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-white/15 backdrop-blur flex items-center justify-center group-hover:bg-white/25 transition">
              <GraduationCap className="w-6 h-6 text-amber-300" />
            </div>
            <div>
              <div className="text-white font-extrabold text-lg tracking-tight leading-none">
                Field Shift
              </div>
              <div className="text-amber-300/70 text-[10px] font-semibold uppercase tracking-[0.2em]">
                Advisor Portal
              </div>
            </div>
          </Link>

          <nav className="flex items-center gap-2">
            <Link
              href="/inbox"
              className="flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-semibold text-white/80 hover:text-white hover:bg-white/10 transition-all"
            >
              <Inbox className="w-4 h-4" />
              <span className="hidden sm:inline">Shared Requests</span>
            </Link>
            <Link
              href="/profile"
              className="flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-semibold text-white/80 hover:text-white hover:bg-white/10 transition-all"
            >
              <User className="w-4 h-4" />
              <span className="hidden sm:inline">Account</span>
            </Link>
            <div className="ml-2 pl-3 border-l border-white/20">
              <UserButton
                appearance={{
                  elements: {
                    avatarBox: "w-9 h-9 ring-2 ring-white/30 ring-offset-2 ring-offset-stone-900",
                  },
                }}
              />
            </div>
          </nav>
        </div>
      </header>

      <main className="flex-1 w-full max-w-6xl mx-auto px-5 py-10">
        {children}
      </main>

      <footer className="bg-gradient-to-r from-stone-800 via-stone-900 to-stone-800 py-5">
        <div className="max-w-6xl mx-auto px-5 flex items-center justify-between text-xs">
          <span className="text-stone-400 font-medium">
            🌾 Field Shift · NASA Space Apps Challenge 2026
          </span>
          <span className="flex items-center gap-2 text-stone-500">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500" />
            </span>
            Demo Mode
          </span>
        </div>
      </footer>
    </div>
  );
}
