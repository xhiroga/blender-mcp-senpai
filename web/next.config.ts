import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // WORKAROUND: Static export configuration for AI SDK
  // This enables the app to be built as static files and served from any static host
  // API routes still work via edge runtime despite static export
  // See: https://github.com/vercel/ai/issues/5140
  output: "export",
  trailingSlash: true,
  basePath: "",
  assetPrefix: "",
  serverExternalPackages: ["ai"]
};

export default nextConfig;
