// pattern: Imperative Shell
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, FileText, Home, LogOut, MessageSquareText, Moon, Sun, Workflow } from "lucide-react";
import { useTheme } from "next-themes";

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

type Props = {
  onLogout?: () => void;
};

export function AppSidebar({ onLogout }: Props) {
  const pathname = usePathname();
  const { resolvedTheme, setTheme } = useTheme();

  return (
    <aside className="hidden md:flex w-56 shrink-0 border-r flex-col bg-background">
      <div className="px-4 h-14 flex items-center font-semibold">qDocent</div>
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
      <div className="mt-auto p-2 border-t space-y-1">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start gap-2 h-9"
          onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
          aria-label="Toggle dark mode"
        >
          {resolvedTheme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
          {resolvedTheme === "dark" ? "Light mode" : "Dark mode"}
        </Button>
        {onLogout && (
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-2 h-9 text-muted-foreground"
            onClick={onLogout}
          >
            <LogOut className="size-4" />
            Sign out
          </Button>
        )}
      </div>
    </aside>
  );
}
