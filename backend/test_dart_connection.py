#!/usr/bin/env python3
"""
DART API 연결 테스트 스크립트
"""
import asyncio
import sys
from config import settings


async def test_dart_api():
    """DART API 연결 테스트"""
    print("=" * 60)
    print("DART API 연결 테스트")
    print("=" * 60)

    # 설정 확인
    print(f"\n[설정 확인]")
    print(f"DART API Key: {settings.dart_api_key[:10]}..." if settings.dart_api_key else "DART API Key: 설정되지 않음")
    print(f"DART Base URL: {settings.dart_base_url}")

    if not settings.dart_api_key:
        print("\n❌ DART API 키가 설정되지 않았습니다.")
        print("backend/.env 파일에 DART_API_KEY를 설정해주세요.")
        sys.exit(1)

    # DART 서비스 테스트
    from app.services.dart_service import dart_service

    try:
        print("\n[테스트 1] 기업 검색 - '삼성전자'")
        companies = await dart_service.search_company("삼성전자")

        if companies:
            print(f"✅ 검색 성공: {len(companies)}개 기업 발견")
            for i, company in enumerate(companies[:3], 1):
                print(f"\n  {i}. {company['corp_name']}")
                print(f"     - 기업코드: {company['corp_code']}")
                print(f"     - 종목코드: {company.get('stock_code', 'N/A')}")
        else:
            print("⚠️  검색 결과가 없습니다.")

        # 삼성전자 상세 정보 조회
        if companies:
            samsung = companies[0]
            print(f"\n[테스트 2] 기업 정보 조회 - {samsung['corp_name']}")

            company_info = await dart_service.get_company_info(samsung['corp_code'])

            if company_info.get('status') == '000':
                print(f"✅ 기업 정보 조회 성공")
                print(f"   - 정식명칭: {company_info.get('corp_name', 'N/A')}")
                print(f"   - 대표이사: {company_info.get('ceo_nm', 'N/A')}")
                print(f"   - 설립일: {company_info.get('est_dt', 'N/A')}")
                print(f"   - 홈페이지: {company_info.get('hm_url', 'N/A')}")
            else:
                print(f"⚠️  응답 상태: {company_info.get('message', '알 수 없음')}")

        print("\n" + "=" * 60)
        print("✅ 모든 테스트 통과!")
        print("=" * 60)
        print("\n다음 명령으로 서버를 시작하세요:")
        print("  cd backend")
        print("  python main.py")
        print("\n또는 Docker Compose 사용:")
        print("  docker-compose up -d")

    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        print("\n가능한 원인:")
        print("1. DART API 키가 유효하지 않음")
        print("2. 네트워크 연결 문제")
        print("3. DART API 서버 응답 지연")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_dart_api())
