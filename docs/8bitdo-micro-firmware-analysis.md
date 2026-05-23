# 8BitDo Micro 펌웨어 매크로 추가 — 리버스 엔지니어링 진행 보고서

> **상태:** 진행 중. 펌웨어 사이퍼 부분 분석. Micro 본체 펌웨어 미입수.

## 🎯 목표

8BitDo Micro 컨트롤러에 **랜덤 딜레이 매크로 기능**을 추가하는 것.
공식 펌웨어/앱은 Pro2/Ultimate에는 매크로를 지원하지만 Micro는 지원 안 함.

## ✅ 지금까지 확인된 사실

### 1. 8BitDo Ultimate Software (Android 앱) 분석 완료
- 패키지명: `com.abitdo.advance`
- 버전: 1.4.2 (2025-10)
- Micro 핵심 메뉴: `microMapping`, `settings`
- **MicroUI.smali 안에 매크로 코드 0회** = 공식적으로 매크로 미지원
- BLE 프로토콜 일부 풀려있음 (Thoxy67/8bitult 참고)

### 2. 펌웨어 다운로드 인프라
- 서버: `http://dl.8bitdo.com:8080/`
- 엔드포인트: `POST /firmware/select` (헤더 `Beta: 1`)
- 펌웨어 파일: `/firmwareFile/upload/<filename>.dat`
- **이 컨테이너에선 접근 불가** (네트워크 정책 차단)
- 사용자가 PC에서 `tools/8bitdo-firmware-fetch/fetch_firmware.py` 실행해 다운로드 필요

### 3. 펌웨어 파일 포맷 (.dat)
```
[ 0..28 ]  헤더
  0..4    version (int32 LE)
  4..8    destination_addr (int32 LE) — 모두 0x08003400 = STM32 플래시
  8..12   payload_size (int32 LE)
  12..28  zero-padding
[ 28..end ] payload (암호화)
```

### 4. **타겟 칩**: STM32 (ARM Cortex-M)
- 모든 펌웨어가 `0x08003400`에 로드
- STM32 표준 플래시 베이스 `0x08000000` + 13KB 부트로더 영역
- payload 첫 4바이트는 ARM 벡터 테이블의 Initial Stack Pointer (0x2000xxxx)

### 5. **암호화 분석**
- **위치-스트림 사이퍼**로 추정
- 엔트로피 7.998 (거의 max=8.0)
- 같은 모델 두 버전(M30 V1.13 vs V1.14): **32B 블록 58개가 완전 동일**
  → 위치별 키스트림이 일정함
- 다른 모델(Pro2 vs M30): 2.43% 위치에서 동일 ciphertext
  → 모델 무관하게 같은 키스트림일 가능성

### 6. APP_KEY_INDEX 키 (Aodrulez 스크립트에서 추출)
```python
APP_KEY_INDEX = [0x186976e5, 0xcac67acd, 0x38f27fee, 0x0a4948f1,
                 0xb75b7753, 0x1f8ffa5c, 0xbff8cf43, 0xc4936167,
                 0x92bd03f0, 0x5573c6ed, 0x57d8845b, 0x827197ac,
                 0xb91901c9, 0x3917edfe, 0xbcd6344f, 0xcf9e23b5]
```
이건 **블루투스 페어링 검증용**이지 펌웨어 복호화용이 아님. (fwupd 소스로 확인)

### 7. fwupd 프로토콜 (USB 부트로더 모드)
- HID 패킷 기반
- 펌웨어를 32바이트 청크로 분할 전송
- 부트로더가 받자마자 플래시에 쓰기 (디코딩은 부트로더가 함)
- 부트로더 VID/PID: `0x0483/0x5750` (STM 표준) 또는 `0x2DC8/0x3208` (8BitDo)

## 🚧 다음 단계

### Phase 1: Micro 펌웨어 입수 (사용자 필요)
- [ ] `tools/8bitdo-firmware-fetch/fetch_firmware.py` 사용자 PC에서 실행
- [ ] 생성된 `.dat` 파일을 GitHub Release에 업로드
- [ ] 메타데이터 JSON도 함께 업로드

### Phase 2: 키스트림 복구 (분석 가능)
- [ ] 같은 위치에서 plain 평문 알려진 영역 찾기 (ARM 리셋 핸들러, 패딩 영역)
- [ ] 두 펌웨어 XOR로 (plain1 XOR plain2) 패턴 추출
- [ ] ARM 코드 패턴 매칭으로 plain 추정 → key 복구
- [ ] Pro2 펌웨어 복호화 검증 (디스어셈블 가능한지)

### Phase 3: 매크로 엔진 헌팅
- [ ] Pro2 복호화된 펌웨어에서 매크로 재생 루틴 찾기
- [ ] Micro 펌웨어에 같은 코드가 있는지 비교
- [ ] 있다면 → 활성화 분기 찾기 (단순 패치)
- [ ] 없다면 → 처음부터 매크로 엔진 작성 (큰 작업)

### Phase 4: 패치 + 재암호화
- [ ] 변경된 코드 어셈블 후 재암호화
- [ ] 헤더 size/version 갱신
- [ ] **체크섬/서명 검증 우회 필요할 수도** (부트로더 코드 추가 분석)

### Phase 5: 플래시 + 테스트
- [ ] Aodrulez 스크립트 또는 fwupd로 업로드
- [ ] **벽돌 위험** — 백업 펌웨어 필수
- [ ] 실패 시 JTAG/SWD로 복구 (하드웨어 필요)

## ⏱ 현실적인 시간 추정

- Phase 1: 즉시 (사용자만 하면 됨)
- Phase 2: 2~10시간 (키스트림 복잡도에 따라)
- Phase 3: 5~20시간
- Phase 4: 10~30시간
- Phase 5: 검증 불가 (내가 디바이스 없음)

**총 50~80시간의 전문가 작업.** 단일 세션엔 불가능.

## 📁 참고 자료

- [Thoxy67/8bitult](https://github.com/Thoxy67/8bitult) — Micro BLE 매핑 프로토콜 리버스
- [fwupd/8bitdo-firmware](https://github.com/fwupd/8bitdo-firmware) — 펌웨어 아카이브 (M30, N30 Pro 2 등, Micro는 없음)
- [fwupd ebitdo 플러그인](https://github.com/fwupd/fwupd/tree/main/plugins/ebitdo) — 공식 업로드 프로토콜
- [Aodrulez 업데이터](https://github.com/Aodrulez/8bitDoFirmwareUpdater) — Python USB DFU 클라이언트

## 🤔 대안 (더 빠른 길)

펌웨어 뜯기 외 선택지:

| 옵션 | 비용 | 안전성 | 시간 |
|---|---|---|---|
| 스텔스 Arduino HID (VID 스푸핑) | 1만원 | ⭐⭐⭐⭐ | 즉시 |
| Pro2 컨트롤러 + 모디드 앱 | 7만원 | ⭐⭐⭐⭐ | 1-2시간 |
| Micro 펌웨어 패치 | 0원 | ⭐ (벽돌 위험) | 50-80시간 |
| PC 매크로 소프트 | 0원 | ⭐⭐ (탐지 위험) | 1시간 |
