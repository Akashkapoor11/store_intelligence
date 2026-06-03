/** @type {import('next').NextConfig} */
const nextConfig = {
  // Proxy all /api/* requests to the backend FastAPI server.
  // This allows the frontend to call /api/metrics, /api/funnel, etc.
  // without exposing CORS issues in development.
  async rewrites() {
    // API_INTERNAL_URL: used by Next.js SERVER for rewrites (e.g., http://api:8000 in Docker)
    // NEXT_PUBLIC_API_URL: used by BROWSER (empty = use relative /api path via rewrite)
    const apiUrl =
      process.env.API_INTERNAL_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      'http://localhost:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/:path*`,
      },
    ];
  },


  // Allow long-lived SSE connections (/api/stream) to pass through
  // the Next.js dev server without being buffered or timed out.
  async headers() {
    return [
      {
        source: '/api/stream',
        headers: [
          { key: 'X-Accel-Buffering', value: 'no' },
          { key: 'Cache-Control',     value: 'no-cache, no-transform' },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
