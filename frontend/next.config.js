/** @type {import('next').NextConfig} */
const nextConfig = {
  // Optimize for mobile
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production'
  },

  // Headers for mobile and security
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-DNS-Prefetch-Control', value: 'on' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Permissions-Policy', value: 'microphone=*, camera=()' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' }
        ]
      }
    ]
  },

  // Disable x-powered-by header
  poweredByHeader: false,

  // Enable Turbopack for faster builds (stable in Next.js 16)
  turbo: {
    rules: {
      '*.svg': {
        loaders: ['@svgr/webpack'],
        as: '*.js',
      },
    },
  },
}

module.exports = nextConfig
