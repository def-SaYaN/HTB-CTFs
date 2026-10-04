/** @type {import('next').NextConfig} */
const nextConfig = {
  // Keep it simple and deterministic for the lab.
  reactStrictMode: false,
  experimental: {
    // Server Actions are enabled by default in 15.x; being explicit for clarity.
    serverActions: {
      bodySizeLimit: "2mb",
    },
  },
};

module.exports = nextConfig;
