import React from "react";
import { NavItem } from "@/components/navigation/NavItem";

export interface AppSidebarProps {
  currentPath?: string;
}

export function AppSidebar({ currentPath = "/app" }: AppSidebarProps) {
  const navItems = [
    {
      href: "/app",
      label: "Overview",
      icon: "📊",
      isComingSoon: false,
    },
    {
      href: "/app/markets",
      label: "Markets",
      icon: "📈",
      isComingSoon: true,
      statusText: "V19",
    },
    {
      href: "/app/regimes",
      label: "Regimes",
      icon: "🧭",
      isComingSoon: true,
      statusText: "V19",
    },
    {
      href: "/app/risk",
      label: "Risk",
      icon: "🛡️",
      isComingSoon: true,
      statusText: "V20",
    },
    {
      href: "/app/backtesting",
      label: "Backtesting",
      icon: "⚡",
      isComingSoon: true,
      statusText: "V20",
    },
    {
      href: "/app/research",
      label: "Research",
      icon: "🔬",
      isComingSoon: true,
      statusText: "V21",
    },
  ];

  return (
    <aside className="app-shell-sidebar" aria-label="Application Sidebar Navigation">
      <div className="sidebar-section">
        <h4 className="sidebar-section-title">Navigation</h4>
        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <NavItem
              key={item.href}
              href={item.href}
              label={item.label}
              icon={item.icon}
              isActive={currentPath === item.href}
              isComingSoon={item.isComingSoon}
              statusText={item.statusText}
            />
          ))}
        </nav>
      </div>

      <div className="sidebar-footer">
        <div className="sidebar-footer-card">
          <p className="sidebar-footer-heading">Platform Architecture</p>
          <p className="sidebar-footer-text">
            Volume 18 establishes the web foundation. Market dashboards and analytics are scheduled for subsequent volumes.
          </p>
        </div>
      </div>
    </aside>
  );
}
