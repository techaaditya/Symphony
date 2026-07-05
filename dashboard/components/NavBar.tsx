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
      <nav className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-8 gap-y-2 px-6 py-4">
        <Link href="/" className="flex flex-col leading-none">
          <span className="font-serif text-2xl font-semibold tracking-tight text-text-primary">
            Symphony
          </span>
          <span className="mt-1 text-xs font-medium tracking-wider text-accent">
            Crisis Management and Coordination Suite
          </span>
        </Link>
        <div className="flex flex-wrap items-center gap-1">
          {LINKS.map((link) => {
            const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-full px-3.5 py-1.5 text-sm transition-all duration-200 ${
                  active
                    ? "bg-accent font-medium text-accent-contrast"
                    : "text-text-secondary hover:bg-surface-2 hover:text-text-primary"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </div>
      </nav>
    </header>
  );
}
