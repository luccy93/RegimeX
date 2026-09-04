/**
 * RegimeX Web — Next.js Configuration
 *
 * Architecture boundary:
 *   - All API communication goes through REGIMEX_API_URL.
 *   - The web application never accesses the database directly.
 *   - Environment variables prefixed with NEXT_PUBLIC_ are exposed to the browser.
 *   - Server-only secrets must NOT use NEXT_PUBLIC_ prefix.
 *
 * @type {import('next').NextConfig}
 */
const nextConfig = {
  // Enable React strict mode for catching potential issues early
  reactStrictMode: true,

  // Expose allowed environment variables to the browser
  // NEXT_PUBLIC_ variables are safe for client-side access
  // Do NOT expose credentials or secrets here
  env: {
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME ?? "RegimeX",
    NEXT_PUBLIC_APP_VERSION: process.env.NEXT_PUBLIC_APP_VERSION ?? "0.1.0",
  },

  // Future: image optimization domains will be added when assets are introduced
  // images: {
  //   remotePatterns: [],
  // },
};

export default nextConfig;
