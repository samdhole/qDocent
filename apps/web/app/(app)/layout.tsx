// pattern: Imperative Shell
"use client";

import { AppSidebar } from "@/components/AppSidebar";
import { LoginCard } from "@/components/LoginCard";
import { useAuthStub } from "@/lib/useAuthStub";

export default function AppGroupLayout({ children }: { children: React.ReactNode }) {
  const { isLoggedIn, login, logout } = useAuthStub();

  return (
    <div className="flex flex-1 min-h-0">
      {isLoggedIn && <AppSidebar onLogout={logout} />}
      <main className="flex-1 min-w-0 overflow-y-auto">
        {isLoggedIn ? children : <LoginCard onLogin={login} />}
      </main>
    </div>
  );
}
