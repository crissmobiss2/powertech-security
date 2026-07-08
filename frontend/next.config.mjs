/** @type {import('next').NextConfig} */
const nextConfig = {
  // standalone output for Docker; Vercel uses its own output pipeline
  ...(process.env.DOCKER_BUILD === "true" ? { output: "standalone" } : {}),
  images: {
    domains: ["localhost", "api.powertech-security.com"],
    remotePatterns: [
      { protocol: "https", hostname: "*.vercel.app" },
      { protocol: "https", hostname: "*.powertech-security.com" },
    ],
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
