# CPU Freq Toggle (갤럭시북이온2 / 윈도우용)

윈도우 전원 옵션의 **"최대 프로세서 상태(%)"** 를 단축키 한 번으로 토글하는 도구.

메이플스토리 라라 무한 강줄기 타기가 고사양 컴에서 50% 확률로만 타지는 문제를
**CPU 다운클럭으로 입력 타이밍 안정화** 시켜서 회피하는 용도로 만든 거임.

## 동작 원리

`powercfg`로 윈도우 전원 옵션의 `PROCTHROTTLEMAX` 값을 즉시 변경.
- AC(충전기 꽂힘) / DC(배터리 모드) 양쪽 모두 동일하게 적용
- 변경 후 활성 프로필 재적용으로 **즉시 반영**
- 별도 드라이버 설치 불필요, 순수 윈도우 기본 API만 사용

## 구성

| 파일 | 용도 |
|---|---|
| `cpu-freq-toggle.ahk` | **AutoHotkey v2** 스크립트 — 트레이 상주 + 글로벌 단축키 |
| `Set-CpuMax.ps1` | **PowerShell** 스크립트 — 인자로 % 받음 |
| `cpu-low.bat` | 50% (살치 모드) 배치 — 더블클릭용 |
| `cpu-mid.bat` | 80% (보통) 배치 |
| `cpu-high.bat` | 100% (고성능) 배치 |

## 권장 사용법: AutoHotkey 버전

1. [AutoHotkey v2](https://www.autohotkey.com/) 설치
2. `cpu-freq-toggle.ahk` 우클릭 → **관리자 권한으로 실행**
3. 트레이 아이콘 상주 확인 후 단축키 사용

### 단축키

| 단축키 | 동작 |
|---|---|
| `Ctrl + Alt + 1` | CPU 50% (살치 모드) |
| `Ctrl + Alt + 2` | CPU 80% (보통) |
| `Ctrl + Alt + 3` | CPU 100% (고성능) |
| `Ctrl + Alt + 0` | 현재 상태 확인 (트레이 알림) |
| `Ctrl + Alt + Q` | 종료 |

### 부팅 시 자동 시작

`Win+R` → `shell:startup` → 열린 폴더에 `cpu-freq-toggle.ahk` 바로가기 복사.
바로가기 속성에서 "고급 → 관리자 권한으로 실행" 체크.

## 대안: PowerShell 버전

AutoHotkey 깔기 싫으면 PowerShell 단독으로 사용 가능.

```powershell
# 살치 모드
.\Set-CpuMax.ps1 -Percent 50

# 평소 모드
.\Set-CpuMax.ps1 -Percent 100
```

관리자 권한이 없으면 자동으로 권한 상승 프롬프트가 뜸.

## 대안: 배치 파일 버전

가장 단순한 버전. 더블클릭만 하면 됨.

- `cpu-low.bat` → 50%
- `cpu-mid.bat` → 80%
- `cpu-high.bat` → 100%

바탕화면에 바로가기 만들고 단축키 바인딩 (속성 → 바로가기 키)도 가능.

## 주의사항

- **관리자 권한 필수**: `powercfg` 변경 권한이 필요함
- **인텔/AMD 모두 호환**: powercfg는 윈도우 표준 API라 CPU 제조사 무관
- **모니터 주사율은 변경 안 함**: 모니터 Hz가 아니라 CPU 최대 사용률(%)만 변경
- **갤럭시북 자체 성능 모드와는 별개**: 삼성 Settings의 모드 변경과는 다른 레이어. 둘 다 만져볼 가치 있음

## 정상 동작 확인

PowerShell이나 cmd에서:

```cmd
powercfg /query SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX
```

`현재 AC 전원 설정 인덱스` / `현재 DC 전원 설정 인덱스` 값이 0x32(=50), 0x50(=80), 0x64(=100)로 변하는지 확인.

## 메이플 라라 살치 권장 루틴

1. `Ctrl + Alt + 1` 눌러서 CPU 50% 모드 진입
2. 메이플 켜고 강줄기 타며 살치
3. 끝나면 `Ctrl + Alt + 3` 으로 100% 복귀

CPU 50%로 다운클럭하면 메이플 FPS가 자연스럽게 떨어지면서 입력 타이밍이
안정화돼서 위방향키 씹힘이 줄어드는 원리.
