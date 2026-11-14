import Link from "next/link";
import {
  ArrowRight,
  Satellite,
  ShieldCheck,
  Sprout,
  Leaf,
} from "lucide-react";

export default function LandingPage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-6 bg-gradient-to-b from-green-950 via-green-900 to-stone-900 relative overflow-hidden">
      {/* Decorative blobs */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-emerald-500/10 rounded-full blur-3xl" />
      <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-amber-500/10 rounded-full blur-3xl" />

      <div className="relative z-10 max-w-3xl text-center space-y-8">
        {/* Badge */}
        <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 backdrop-blur border border-white/10 text-emerald-300 text-sm font-bold">
          <Satellite className="w-4 h-4" />
          NASA Space Apps Challenge 2026
        </span>

        {/* Title */}
        <div className="space-y-4">
          <div className="flex items-center justify-center gap-3">
            <Leaf className="w-10 h-10 text-emerald-400 -rotate-12" />
            <h1 className="text-6xl sm:text-7xl font-black text-white tracking-tight">
              Field{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-green-300">
                Shift
              </span>
            </h1>
            <Leaf className="w-10 h-10 text-emerald-400 rotate-12 scale-x-[-1]" />
          </div>
          <p className="text-lg sm:text-xl text-stone-300 max-w-xl mx-auto leading-relaxed">
            Adapting smallholder farms with 20+ years of NASA Earth
            observations, harmonized with Kerala ground truth.
          </p>
        </div>

        {/* Feature cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 pt-4">
          {[
            {
              Icon: Sprout,
              title: "3 Strategy Cards",
              desc: "Customary rotation plus two climate-resilient alternative crops.",
              gradient: "from-emerald-500/20 to-green-600/20",
              iconColor: "text-emerald-400",
            },
            {
              Icon: Satellite,
              title: "Stress Diagnosis",
              desc: "Detect rainfall deficits & heat stress across past seasons.",
              gradient: "from-amber-500/20 to-yellow-600/20",
              iconColor: "text-amber-400",
            },
            {
              Icon: ShieldCheck,
              title: "Consent & Privacy",
              desc: "Selective snapshot sharing with student mentors & extension officers.",
              gradient: "from-teal-500/20 to-cyan-600/20",
              iconColor: "text-teal-400",
            },
          ].map((card) => (
            <div
              key={card.title}
              className={`p-6 rounded-2xl bg-gradient-to-br ${card.gradient} backdrop-blur border border-white/10 text-left hover:border-white/20 hover:-translate-y-1 transition-all duration-300`}
            >
              <card.Icon className={`w-8 h-8 ${card.iconColor} mb-3`} />
              <h3 className="font-extrabold text-white text-base">
                {card.title}
              </h3>
              <p className="text-stone-400 text-sm mt-1.5 leading-relaxed">
                {card.desc}
              </p>
            </div>
          ))}
        </div>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row gap-4 pt-6 justify-center">
          <Link
            href="/login"
            className="inline-flex items-center justify-center gap-2 h-14 px-10 rounded-2xl bg-gradient-to-r from-emerald-500 to-green-600 text-white font-bold text-lg shadow-xl shadow-emerald-500/25 hover:shadow-2xl hover:shadow-emerald-500/30 hover:-translate-y-0.5 transition-all"
          >
            Sign In <ArrowRight className="w-5 h-5" />
          </Link>
          <Link
            href="/register"
            className="inline-flex items-center justify-center h-14 px-10 rounded-2xl bg-white/10 backdrop-blur border border-white/20 text-white font-bold text-lg hover:bg-white/20 transition-all"
          >
            Create Account
          </Link>
        </div>
      </div>
    </main>
  );
}
