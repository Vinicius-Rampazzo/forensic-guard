import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// Metadata alimenta o <title> e as meta tags da pagina. Como layout.tsx e um
// Server Component, o Next resolve isso na renderizacao, sem JavaScript extra
// no navegador.
export const metadata: Metadata = {
  title: "ForensicGuard — Digital Evidence Analyzer",
  description:
    "Open-source forensic triage tool for inspecting files, images and emails for suspicious indicators, metadata anomalies and potential security threats.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
