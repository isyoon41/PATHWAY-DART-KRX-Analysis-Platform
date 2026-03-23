import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import ErrorBoundary from '@/components/ErrorBoundary'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'DART·KRX 기업분석 플랫폼',
  description: '실시간 기업 분석 및 근거 기반 리포트 생성',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko">
      <body className={inter.className}>
        <div className="min-h-screen bg-gray-50">
          <ErrorBoundary fallbackMessage="앱 전체에서 오류가 발생했습니다. 페이지를 새로고침 해주세요.">
            {children}
          </ErrorBoundary>
        </div>
      </body>
    </html>
  )
}
