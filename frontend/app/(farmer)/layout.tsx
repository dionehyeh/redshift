import Link from "next/link";
import { UserButton } from "@clerk/nextjs";
import { Sprout } from "lucide-react";

export default function FarmerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <header className="sticky top-0 z-40 bg-white border-b border-slate-200 px-4 py-3">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <Link href="/fields" className="flex items-center gap-2">
            <div className="p-2 bg-emerald-100 text-emerald-800 rounded-xl">
              <Sprout className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-slate-900 leading-none block">Field Shift</span>
              <span className="text-xs text-slate-500">Kerala Demo Farm</span>
            </div>
          </Link>

          <nav className="flex items-center gap-4 text-sm font-medium">
            <Link href="/fields" className="text-slate-700 hover:text-emerald-700">
              My Fields
            </Link>
            <Link href="/about" className="text-slate-700 hover:text-emerald-700">
              About Data
            </Link>
            <Link href="/profile" className="text-slate-700 hover:text-emerald-700">
              Account
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
