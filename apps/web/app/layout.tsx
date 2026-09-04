import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "RegimeX — Market Intelligence Platform",
    template: "%s | RegimeX",
  },
  description:
    "Open-source market intelligence and quantitative research platform. " +
    "Understand market regimes, analyze risk, and explore quantitative strategies.",
  keywords: [
    "market regime",
    "quantitative finance",
    "regime detection",
    "risk analytics",
    "backtesting",
    "open-source",
  ],
  authors: [{ name: "RegimeX Contributors" }],
  robots: {
    index: true,
    follow: true,
  },
};

/**
 * Root layout — applied to all pages.
 *
 * Architecture boundary:
 *   - This layout wraps the entire application.
 *   - Global styles are imported here.
 *   - No business logic belongs in the layout.
 *   - Authentication context providers will be added in V15.
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
