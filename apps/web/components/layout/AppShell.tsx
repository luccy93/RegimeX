import React from "react";
import { AppHeader } from "./AppHeader";
import { AppSidebar } from "./AppSidebar";

export interface AppShellProps {
  children: React.ReactNode;
  currentPath?: string;
}

export function AppShell({ children, currentPath }: AppShellProps) {
  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-to-content">
        Skip to main content
      </a>
      <AppHeader />
      <div className="app-shell-body">
        <AppSidebar currentPath={currentPath} />
        <main id="main-content" className="app-shell-main" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  );
}
