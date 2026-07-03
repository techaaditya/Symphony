"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Overview" },
  { href: "/live", label: "Live" },
  { href: "/ledger", label: "Ledger" },
  { href: "/conflicts", label: "Conflicts" },
  { href: "/benchmark", label: "Benchmark" },
];

export default function NavBar() {
  const pathname = usePathname();

  return (
    <header className="border-b border-border bg-surface-1">
      <nav className="mx-auto flex max-w-6xl items-center gap-1 px-6 py-3">
        <span className="mr-4 text-sm font-semibold tracking-tight text-text-primary">
          Symphony
        </span>
        {LINKS.map((link) => {
          const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
                active
                  ? "bg-page-plane text-text-primary"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
