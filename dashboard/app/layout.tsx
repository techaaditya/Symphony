import type { Metadata } from "next";
import { Cormorant_Garamond, Inter } from "next/font/google";
import NavBar from "@/components/NavBar";
import "./globals.css";

// Editorial serif for the brand lockup and page headings; a clean grotesque
// for everything else (nav, body copy, data). Loaded once here and exposed
// as CSS variables so globals.css can assign them to the --font-* tokens
// without every component importing next/font itself.
const serif = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-serif",
});

const sans = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "Symphony | Crisis Management and Coordination Suite",
  description:
    "Five specialist agents negotiate scarce disaster-response resources via the Parliament Protocol. Agents propose, deterministic code adjudicates.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`h-full ${serif.variable} ${sans.variable}`}>
      <body className="min-h-full flex flex-col font-sans">
        <NavBar />
        <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
