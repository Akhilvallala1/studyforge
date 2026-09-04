"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS: { href: string; label: string }[] = [
  { href: "/", label: "Today" },
  { href: "/courses", label: "Courses" },
  { href: "/usage", label: "Usage" },
];

/** "/" only matches itself; every other tab owns its whole subtree. */
function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function SiteHeader() {
  const pathname = usePathname();

  // A review session runs under its own top bar (End session, progress, position),
  // and two stacked bars would push the card below the fold on a laptop screen.
  if (pathname === "/review" || pathname.startsWith("/review/")) return null;

  return (
    <header className="border-b border-border">
      <nav className="mx-auto flex w-full max-w-4xl items-center justify-between px-6 py-3">
        <Link href="/" className="text-subtitle tracking-tight text-text">
          StudyForge
        </Link>
        <div className="flex items-center gap-5 text-ui">
          {LINKS.map((link) => {
            const active = isActive(pathname, link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                // The accent is spent here on purpose: it is one of the three places
                // this design allows it (focus rings, inline links, the active
                // nav/tab indicator), never as a fill.
                className={
                  active
                    ? "font-medium text-accent"
                    : "text-text-muted transition-colors duration-fast ease-standard hover:text-text"
                }
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
