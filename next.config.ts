import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/game/:path*',
        destination: process.env.NODE_ENV === 'development'
          ? 'http://127.0.0.1:5328/api/game/:path*'
          : '/api/index',
      },
      {
        source: '/api/rules/:path*',
        destination: process.env.NODE_ENV === 'development'
          ? 'http://127.0.0.1:5328/api/rules/:path*'
          : '/api/index',
      },
    ];
  },
};

export default nextConfig;
