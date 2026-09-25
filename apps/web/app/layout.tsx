import type { Metadata, Viewport } from "next";
import "./globals.css";

export const viewport: Viewport = {
  themeColor: "#090d16",
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export const metadata: Metadata = {
  title: {
    default: "RegimeX — Open-Source Market Intelligence Platform",
    template: "%s | RegimeX",
  },
  description:
    "Open-source market intelligence and quantitative research platform. " +
    "Understand market regimes, analyze transition dynamics, and evaluate systematic cross-regime risk.",
  keywords: [
    "market regimes",
    "quantitative research",
    "regime detection",
    "transition analytics",
    "risk intelligence",
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
 * Root Layout — wraps the entire RegimeX web application.
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
