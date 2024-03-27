"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { BookOpen, Brain, ChevronRight, FileText, Layers, Target, Zap } from "lucide-react";

const FEATURES = [
  {
    icon: Layers,
    title: "Syllabus Knowledge Graph",
    desc: "Your syllabus becomes an interactive DAG. Click any topic to dive deep.",
    gradient: "from-indigo-500 to-violet-500",
  },
  {
    icon: Brain,
    title: "Grounded AI Tutor",
    desc: "Every answer cites a page from your textbook. Zero hallucination. Pure signal.",
    gradient: "from-violet-500 to-purple-500",
  },
  {
    icon: BookOpen,
    title: "PDF Auto-Navigation",
    desc: "Click a citation → PDF jumps to that exact paragraph and highlights it.",
    gradient: "from-purple-500 to-pink-500",
  },
  {
    icon: Target,
    title: "Deviation Tracking",
    desc: "Go on any tangent. SYL tracks where you left off. Resume on one click.",
    gradient: "from-pink-500 to-rose-500",
  },
  {
    icon: Zap,
    title: "Problem Ranker",
    desc: "Problems ranked by exam likelihood from your professor's note coverage.",
    gradient: "from-rose-500 to-orange-500",
  },
  {
    icon: FileText,
    title: "Hybrid OCR Pipeline",
    desc: "Works on scanned notes, WhatsApp PDFs, handwritten sheets — everything.",
    gradient: "from-amber-500 to-yellow-500",
  },
];

const STEPS = [
  { num: "01", title: "Upload", desc: "Syllabus + textbook + professor notes" },
  { num: "02", title: "Explore", desc: "Interactive knowledge graph auto-generated" },
  { num: "03", title: "Study", desc: "AI tutor answers with page citations from your books" },
  { num: "04", title: "Track", desc: "Deviation detected, resume from exact deviation point" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gray-950 overflow-hidden">
      {/* Nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center">
              <Brain className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-white text-lg tracking-tight">SYL</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/auth/login" className="text-sm text-gray-400 hover:text-white transition-colors">
              Sign in
            </Link>
            <Link
              href="/auth/signup"
              className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm px-4 py-2 rounded-lg font-medium transition-colors"
            >
              Get started free
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-36 pb-24 px-6 relative">
        {/* Background glow */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-indigo-600/10 rounded-full blur-3xl" />
          <div className="absolute top-1/3 left-1/3 w-[400px] h-[400px] bg-violet-600/10 rounded-full blur-3xl" />
        </div>

        <div className="max-w-5xl mx-auto text-center relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center gap-2 glass px-4 py-2 rounded-full text-sm text-indigo-300 mb-8">
              <div className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse" />
              Now in beta — free for students
            </div>

            <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-8 leading-tight">
              Study smarter with{" "}
              <span className="gradient-text">AI that reads your books</span>
            </h1>

            <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-12 leading-relaxed">
              Upload your syllabus, textbook and professor notes. SYL builds a knowledge graph,
              answers questions with exact page citations, and never lets you lose your place.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                href="/auth/signup"
                id="cta-get-started"
                className="group flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-4 rounded-xl font-semibold text-lg transition-all glow-indigo hover:scale-105"
              >
                Start studying for free
                <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link
                href="/demo"
                id="cta-demo"
                className="flex items-center justify-center gap-2 glass hover:bg-white/10 text-white px-8 py-4 rounded-xl font-semibold text-lg transition-all"
              >
                Try the demo
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-24 px-6 relative">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              How it works
            </h2>
            <p className="text-gray-400 text-lg">Four steps from upload to mastery</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {STEPS.map((step, i) => (
              <motion.div
                key={step.num}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1, duration: 0.5 }}
                viewport={{ once: true }}
                className="glass rounded-2xl p-6 text-center relative"
              >
                <div className="text-4xl font-black gradient-text mb-3">{step.num}</div>
                <h3 className="font-bold text-white text-lg mb-2">{step.title}</h3>
                <p className="text-gray-400 text-sm">{step.desc}</p>
                {i < STEPS.length - 1 && (
                  <div className="hidden md:block absolute top-1/2 -right-3 w-6 h-6 text-indigo-500">
                    <ChevronRight className="w-6 h-6" />
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">Everything you need to ace it</h2>
            <p className="text-gray-400 text-lg">Built for real students with real university materials</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map((feature, i) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.08, duration: 0.5 }}
                viewport={{ once: true }}
                className="glass rounded-2xl p-6 group hover:bg-white/5 transition-colors"
              >
                <div
                  className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}
                >
                  <feature.icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="font-bold text-white text-lg mb-2">{feature.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{feature.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-6">
        <div className="max-w-3xl mx-auto text-center glass rounded-3xl p-12">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Stop re-reading the same chapter
          </h2>
          <p className="text-gray-400 text-lg mb-8">
            Join students who study with AI that actually knows their course material.
          </p>
          <Link
            href="/auth/signup"
            className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-4 rounded-xl font-semibold text-lg transition-all hover:scale-105"
          >
            Get started — it's free
            <ChevronRight className="w-5 h-5" />
          </Link>
          <p className="text-gray-500 text-sm mt-4">
            No credit card required · 50 messages/day free · 200 pages/syllabus
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-8 px-6">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-indigo-400" />
            <span className="font-bold text-white">SYL</span>
          </div>
          <p className="text-gray-500 text-sm">
            Built by{" "}
            <a href="https://github.com/Hrushikesh-ramilla" className="text-indigo-400 hover:text-indigo-300">
              Hrushikesh Ramilla
            </a>{" "}
            · ABV-IIITM Gwalior
          </p>
          <p className="text-gray-600 text-sm">MIT License</p>
        </div>
      </footer>
    </div>
  );
}
