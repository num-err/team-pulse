// Static export for GitHub Pages is opt-in via NEXT_PUBLIC_DEMO_MODE=true, so
// local dev (`npm run dev`) against the real API is unchanged.
// NEXT_PUBLIC_BASE_PATH is the repo subpath Pages serves from, e.g. "/team-pulse".
const isStaticDemo = process.env.NEXT_PUBLIC_DEMO_MODE === "true";
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

/** @type {import('next').NextConfig} */
const nextConfig = isStaticDemo
  ? {
      output: "export",
      basePath,
      trailingSlash: true,
      images: { unoptimized: true },
    }
  : {};

export default nextConfig;
