import React from "react";
import { AppShell } from "@/components/layout/AppShell";

export const metadata = {
  title: "Console",
};

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppShell>{children}</AppShell>;
}
