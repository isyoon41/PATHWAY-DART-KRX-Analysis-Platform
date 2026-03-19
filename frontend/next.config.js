/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // 백엔드 API를 프록시 → 미리보기 환경에서 포트 3000 하나로 통합
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ]
  },
}

module.exports = nextConfig
