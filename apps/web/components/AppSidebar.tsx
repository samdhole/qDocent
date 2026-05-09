// pattern: Imperative Shell
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { MessageSquareText, FileText, Workflow, BarChart3, Home } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

const NAV_ITEMS = [
  { href: "/", label: "Home", icon: Home },
  { href: "/ask", label: "Ask", icon: MessageSquareText },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/workflows", label: "Workflows", icon: Workflow },
  { href: "/evals", label: "Evaluations", icon: BarChart3 },
] as const;

export function AppSidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden md:flex w-56 shrink-0 border-r flex-col bg-background">
      <div className="px-4 h-14 flex items-center font-semibold">DocQuery</div>
      <Separator />
      <nav className="flex flex-col gap-1 p-2">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <Button
              key={href}
              asChild
              variant={active ? "secondary" : "ghost"}
              className={cn("justify-start gap-2 h-9", active && "font-medium")}
            >
              <Link href={href}>
                <Icon className="size-4" />
                {label}
              </Link>
            </Button>
          );
        })}
      </nav>
    </aside>
  );
}
