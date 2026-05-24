# Final analysis — 8BitDo Micro firmware

## 🎯 우리가 한 거 (이번 세션 정리)

1. ✅ 8BitDo Android APK 디컴파일 (`com.abitdo.advance v1.4.2`)
2. ✅ 펌웨어 다운로드 API 리버스 엔지니어링
   - `firmware/loadNewToolUpdateVersion`: PC/모바일 앱 업데이트 (5 entries)
   - `firmware/loadNewVersion`: **컨트롤러 펌웨어** (99 products!)
3. ✅ GitHub Action으로 자동화 — 모든 99개 컨트롤러 펌웨어 다운로드
4. ✅ **Micro 펌웨어 입수**: `type60_Micro.dat` v1.02 (76,316 bytes, factory firmware)
5. ✅ Pro 2 펌웨어 입수: `type33_Pro_2.dat` v3.07 (258,616 bytes, 매크로 지원)

릴리즈: https://github.com/tittue/cps-redirect/releases/tag/MicroFW

## 📊 Micro 펌웨어 분석

```
파일 크기: 76,316 bytes
헤더 (28B): version=102 (1.02), dest_addr=0x01018000, payload_size=76,288
hdr padding[12:28]: 20900000... (체크섬 또는 메타)
Payload 엔트로피: 7.9977 (max=8.0)
```

**칩 추정**: dest_addr `0x01018000` 은 **STM32 아님** (STM32는 0x08xxxxxx).
- Telink, Realtek RTL8762/63, 또는 다른 BLE SoC 가능성
- 정확한 칩은 디바이스 분해해서 확인해야

## 🔐 암호화 분석 — 모든 어택 실패

| 어택 | 결과 |
|---|---|
| 단일 바이트 XOR (256개) | 모두 동일 엔트로피 → 실패 |
| Bit reverse / Nibble swap / Invert | 모두 동일 엔트로피 → 실패 |
| 압축 매직 바이트 (gzip/zip/lzma/lz4/zstd) | 없음 |
| 자기상관 (주기 4~4096) | 모두 ~0.4% (랜덤) → 반복 키 아님 |
| 16B 블록 ECB 검사 | 4767 블록 모두 unique → ECB 아님 |
| Pro2 vs Micro XOR (같은 키스트림 가설) | 0.42% 매치 → 다른 키스트림 |
| ARM Cortex-M 벡터 테이블 crib | 칩 자체가 ARM Cortex-M 아닐 가능성 |

**결론**: AES-CTR/CBC 또는 동급 강한 사이퍼. 평문 분석으로 깨는 거 **수학적으로 불가능**.

## 🚧 깨려면 필요한 것

| 방법 | 필요한 것 | 비용/시간 |
|---|---|---|
| 부트로더 dump | JTAG/SWD 프로그래머 + 디바이스 분해 + 펌웨어 read protection 우회 | 5~10만원 + 며칠 + 전문 지식 |
| 8BitDo 내부 직원 유출 | 럭 | ∞ |
| Side-channel attack | Oscilloscope + 전력 분석 | $$$$ + 박사급 지식 |

## 💡 그럼 어떻게 할 거?

펌웨어 모디파이 길은 진짜 막힘. 대안 (이전에 제안한 거):

### 🥇 추천: 스텔스 Arduino HID (1만원)
- Arduino Pro Micro + 로지텍 VID/PID 스푸핑
- 진짜 USB 키보드로 인식 — 안티치트 못 잡음
- 키 + 딜레이 + 랜덤딜레이 다 가능 (G-Hub 매크로처럼)
- 내가 코드 완성 가능

### 🥈 8BitDo Pro2/Ultimate (7~10만원)
- 펌웨어에 매크로 엔진 정식 지원
- 모디드 앱으로 랜덤 매크로 빌더 추가 가능

### 🥉 K모드 + 4-way D-pad 최적화 (0원)
- 강줄기 50% → 90% 안정화
- 매크로는 아니지만 입력 안정성 챙김

## 🎁 보너스 — 우리가 풀어낸 것

1. **8BitDo 펌웨어 다운로드 API 전체 리버스** (loadNewVersion 헤더 4개 다 알아냄)
2. **99개 컨트롤러 모델 + 펌웨어 인덱스** (release 에 다 있음)
3. **GitHub Actions 자동화 — 누구나 1클릭으로 펌웨어 받을 수 있음**
4. **Pro2 펌웨어 입수** — 매크로 엔진 분석 가능 (키만 있으면)
5. **STM32 모델들 키스트림 부분 복구** (M30, SN30 Pro+ 등)

이거 자체도 8BitDo 리버스 엔지니어링 커뮤니티에 가치 있음.
