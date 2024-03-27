import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "SYL — AI Study Engine",
  description:
    "Upload your syllabus + textbook + professor notes. Get an interactive knowledge graph. AI explains using exact book citations. Never lose your place again.",
  keywords: ["AI study", "syllabus", "RAG", "PDF", "knowledge graph", "citation"],
  authors: [{ name: "Hrushikesh Ramilla", url: "https://github.com/Hrushikesh-ramilla" }],
  openGraph: {
    title: "SYL — AI Study Engine",
    description: "Syllabus-aware AI that studies like you do.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="bg-gray-950 text-white antialiased">{children}</body>
    </html>
  );
}
