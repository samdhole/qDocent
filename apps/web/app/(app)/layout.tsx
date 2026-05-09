// pattern: Imperative Shell
"use client";

import { AppSidebar } from "@/components/AppSidebar";
import { LoginCard } from "@/components/LoginCard";
import { useAuthStub } from "@/lib/useAuthStub";

export default function AppGroupLayout({ children }: { children: React.ReactNode }) {
  const { isLoggedIn, login, logout } = useAuthStub();

  if (!isLoggedIn) {
    return (
      <div className="flex flex-1 min-h-0">
        <main className="flex-1 min-w-0 overflow-y-auto">
          <LoginCard onLogin={login} />
        </main>
      </div>
    );
  }

  return (
    <div className="flex flex-1 min-h-0">
      <AppSidebar onLogout={logout} />
      <main className="flex-1 min-w-0 overflow-y-auto">{children}</main>
    </div>
  );
}
