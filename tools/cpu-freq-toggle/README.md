# CPU Freq Toggle (갤럭시북이온2 / 윈도우용)

윈도우 전원 옵션의 **"최대 프로세서 상태(%)"** 를 더블클릭 한 번으로 전환하는 도구.

메이플스토리 라라 무한 강줄기 타기가 고사양 컴에서 50% 확률로만 타지는 문제를
**CPU 다운클럭으로 입력 타이밍 안정화** 시켜서 회피하는 용도.

## ⚠️ 안티치트 안전성

- ✅ **키보드/마우스 후킹 없음** — VBS와 Python 모두 단순히 윈도우 표준 명령 `powercfg`를 호출함
- ✅ **게임 프로세스 메모리 접근 없음** — 메이플 클라이언트와 무관하게 동작
- ❌ AutoHotkey 같은 매크로 도구는 일부 게임에서 탐지될 수 있어 **이번 버전에서는 사용하지 않음**

## 🚀 가장 빠른 시작

1. 이 폴더 전체를 다운로드
2. **`Install-To-Desktop.bat` 더블클릭** → 바탕화면에 "CPU Freq Toggle" 폴더 자동 생성
3. 바탕화면 폴더에서 원하는 VBS 더블클릭
   - `cpu-low.vbs` → 50% (살치 모드)
   - `cpu-mid.vbs` → 80%
   - `cpu-high.vbs` → 100% (평소)
   - `cpu-toggle.vbs` → 자동 토글 (50% ↔ 100%)
4. UAC 권한 요청에 "예" 클릭. 끝.

## 구성

### VBS 버전 (추천, 별도 설치 불필요)

| 파일 | 동작 |
|---|---|
| `cpu-low.vbs` | CPU 50% — 살치 모드 |
| `cpu-mid.vbs` | CPU 80% — 보통 |
| `cpu-high.vbs` | CPU 100% — 고성능 |
| `cpu-toggle.vbs` | 50% ↔ 100% 자동 토글 |

- 콘솔 창 없이 백그라운드 실행
- UAC 권한 요청 후 즉시 적용
- 2초간 안내 팝업

### Python 버전 (대안)

| 파일 | 용도 |
|---|---|
| `cpu_freq.py` | 메인 스크립트 |
| `cpu-low-py.vbs` | 파이썬 50% 호출 래퍼 |
| `cpu-high-py.vbs` | 파이썬 100% 호출 래퍼 |

```bash
# CLI에서 직접 호출
python cpu_freq.py 50          # 살치 모드
python cpu_freq.py 100         # 평소 모드
python cpu_freq.py --status    # 현재 상태 조회
```

파이썬 설치 안 됐으면 VBS 단독 버전 쓰면 됨.

### 기타

| 파일 | 용도 |
|---|---|
| `Install-To-Desktop.bat` | 바탕화면에 자동 설치 |
| `Set-CpuMax.ps1` | PowerShell 단독 버전 |
| `cpu-low.bat` / `cpu-mid.bat` / `cpu-high.bat` | 콘솔 배치 (덜 권장) |

## 동작 원리

```
powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX <N>
powercfg /setdcvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX <N>
powercfg /setactive SCHEME_CURRENT
```

- `PROCTHROTTLEMAX` = 최대 프로세서 상태 (%)
- AC = 충전기 꽂힌 상태, DC = 배터리 모드 → 둘 다 적용
- `setactive` 로 즉시 반영

## 정상 동작 확인

PowerShell이나 cmd에서:

```cmd
powercfg /query SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX
```

`현재 AC 전원 설정 인덱스` 값이 `0x32`(=50), `0x50`(=80), `0x64`(=100)로 변하면 정상.

## 메이플 라라 살치 권장 루틴

1. `cpu-low.vbs` 더블클릭 → UAC 승인 → "CPU 50% (살치 모드)" 팝업
2. 메이플 켜고 강줄기 살치
3. 끝나면 `cpu-high.vbs` 더블클릭 → 평소 모드 복귀

또는 `cpu-toggle.vbs` 하나만 두고 매번 클릭해서 토글.

## 주의사항

- **관리자 권한 필수** — UAC 매번 뜸 (작업 스케줄러로 우회 가능, 필요 시 추가)
- **갤럭시북 자체 성능 모드와는 별개 레이어** — Samsung Settings의 모드와 동시 사용 가능
- **CPU 50% 설정은 영구적** — 다음 부팅에도 유지. 평소 사용 시 답답하면 100%로 복귀 필요
