import React from "react";
import Link from "next/link";
import { cn } from "@/lib/utils/cn";
import { Badge } from "@/components/ui/Badge";

export interface NavItemProps {
  href: string;
  label: string;
  icon?: React.ReactNode;
  isActive?: boolean;
  isComingSoon?: boolean;
  statusText?: string;
  badge?: string;
}

export function NavItem({
  href,
  label,
  icon,
  isActive = false,
  isComingSoon = false,
  statusText,
  badge,
}: NavItemProps) {
  if (isComingSoon) {
    return (
      <div
        className={cn(
          "nav-item nav-item-disabled",
          isActive && "nav-item-active"
        )}
        aria-disabled="true"
        title={`${label} (Scheduled for future volume)`}
      >
        {icon && <span className="nav-item-icon" aria-hidden="true">{icon}</span>}
        <span className="nav-item-label">{label}</span>
        {statusText && (
          <Badge variant="outline" size="sm" className="nav-item-badge">
            {statusText}
          </Badge>
        )}
      </div>
    );
  }

  return (
    <Link
      href={href}
      className={cn(
        "nav-item",
        isActive && "nav-item-active"
      )}
      aria-current={isActive ? "page" : undefined}
    >
      {icon && <span className="nav-item-icon" aria-hidden="true">{icon}</span>}
      <span className="nav-item-label">{label}</span>
      {badge && (
        <Badge variant="info" size="sm" className="nav-item-badge">
          {badge}
        </Badge>
      )}
    </Link>
  );
}
