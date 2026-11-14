import Link from "next/link";
import { ArrowRight, Satellite, ShieldCheck, Sprout } from "lucide-react";

export default function LandingPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-6 bg-gradient-to-b from-emerald-50 to-slate-100">
      <div className="max-w-2xl text-center space-y-6">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-100 text-emerald-800 text-sm font-semibold">
          <Satellite className="w-4 h-4" /> NASA Space Apps Challenge 2026
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold text-slate-900 tracking-tight">
          Field Shift
        </h1>
        <p className="text-xl text-slate-700">
          Adapting smallholder farms with 20+ years of NASA Earth observations, harmonized with local Kerala ground truth.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 text-left">
          <div className="p-4 rounded-xl bg-white shadow-sm border border-slate-200">
            <Sprout className="w-6 h-6 text-emerald-600 mb-2" />
            <h3 className="font-bold text-slate-900">3 Strategy Cards</h3>
            <p className="text-xs text-slate-600 mt-1">Customary rotation plus two climate-resilient alternative crops.</p>
          </div>
          <div className="p-4 rounded-xl bg-white shadow-sm border border-slate-200">
            <Satellite className="w-6 h-6 text-emerald-600 mb-2" />
            <h3 className="font-bold text-slate-900">Stress Diagnosis</h3>
            <p className="text-xs text-slate-600 mt-1">Detect rainfall deficits & heat stress across past seasons.</p>
          </div>
          <div className="p-4 rounded-xl bg-white shadow-sm border border-slate-200">
            <ShieldCheck className="w-6 h-6 text-emerald-600 mb-2" />
            <h3 className="font-bold text-slate-900">Consent & Privacy</h3>
            <p className="text-xs text-slate-600 mt-1">Selective snapshot sharing with student mentors & extension officers.</p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 pt-6 justify-center">
          <Link
            href="/login"
            className="inline-flex items-center justify-center gap-2 h-12 px-8 rounded-xl bg-emerald-700 text-white font-medium hover:bg-emerald-800 transition"
          >
            Sign In <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/register"
            className="inline-flex items-center justify-center h-12 px-8 rounded-xl bg-white border border-slate-300 text-slate-800 font-medium hover:bg-slate-50 transition"
          >
            Create Account
          </Link>
          <Link
            href="/about"
            className="inline-flex items-center justify-center h-12 px-6 rounded-xl text-slate-600 hover:text-slate-900 transition"
          >
            About Analysis
          </Link>
        </div>
      </div>
    </main>
  );
}
