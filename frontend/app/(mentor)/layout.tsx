import Link from "next/link";
import { UserButton } from "@clerk/nextjs";
import { GraduationCap } from "lucide-react";

export default function MentorLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <header className="sticky top-0 z-40 bg-white border-b border-slate-200 px-4 py-3">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <Link href="/inbox" className="flex items-center gap-2">
            <div className="p-2 bg-blue-100 text-blue-800 rounded-xl">
              <GraduationCap className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-slate-900 leading-none block">Field Shift Advisor Portal</span>
              <span className="text-xs text-slate-500">Student Mentor & Extension Review</span>
            </div>
          </Link>

          <nav className="flex items-center gap-4 text-sm font-medium">
            <Link href="/inbox" className="text-slate-700 hover:text-blue-700">
              Shared Requests
            </Link>
            <UserButton />
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-5xl w-full mx-auto p-4 sm:p-6 pb-20 sm:pb-6">
        {children}
      </main>
    </div>
  );
}
