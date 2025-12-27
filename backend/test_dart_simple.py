#!/usr/bin/env python3
"""
DART API 간단 테스트
"""
import asyncio
import httpx
from config import settings


async def test_simple():
    """간단한 DART API 테스트"""
    print("=" * 60)
    print("DART API 간단 테스트")
    print("=" * 60)

    print(f"\nAPI Key: {settings.dart_api_key[:10]}...")
    print(f"Base URL: {settings.dart_base_url}\n")

    # 공시 검색 API 테스트 (삼성전자 공시 조회)
    # 삼성전자 corp_code: 00126380
    url = f"{settings.dart_base_url}/list.json"
    params = {
        "crtfc_key": settings.dart_api_key,
        "corp_code": "00126380",  # 삼성전자
        "bgn_de": "20240101",
        "end_de": "20241231",
        "page_no": 1,
        "page_count": 5
    }

    print("[테스트] 삼성전자 공시 목록 조회")
    print(f"URL: {url}")
    print(f"Parameters: corp_code={params['corp_code']}, bgn_de={params['bgn_de']}, end_de={params['end_de']}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=30.0)

            print(f"\n상태 코드: {response.status_code}")
            print(f"응답 헤더: {dict(response.headers)}")

            if response.status_code == 200:
                data = response.json()
                print(f"\n응답 데이터:")
                print(f"- 상태: {data.get('status')}")
                print(f"- 메시지: {data.get('message')}")

                if data.get('status') == '000':
                    print("\n✅ API 연결 성공!")
                    if 'list' in data and len(data['list']) > 0:
                        print(f"\n공시 목록 ({len(data['list'])}건):")
                        for i, item in enumerate(data['list'][:3], 1):
                            print(f"\n  {i}. {item.get('report_nm')}")
                            print(f"     - 접수일: {item.get('rcept_dt')}")
                            print(f"     - 제출인: {item.get('flr_nm')}")
                    else:
                        print("\n⚠️  공시 목록이 없습니다.")
                elif data.get('status') == '013':
                    print("\n⚠️  조회된 데이터가 없습니다.")
                else:
                    print(f"\n⚠️  API 응답 오류: {data.get('message')}")
            else:
                print(f"\n❌ HTTP 오류: {response.status_code}")
                print(f"응답 내용: {response.text[:500]}")

    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_simple())
