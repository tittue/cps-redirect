"""
8BitDo 펌웨어 키스트림 추출 / 복호화 분석 파이프라인

기반 가설:
- 모든 8BitDo STM32 펌웨어는 같은 위치-스트림 사이퍼 사용
- 즉 keystream[i] 는 위치 i 에서 모든 펌웨어에 동일
- ciphertext[i] = plaintext[i] XOR keystream[i]

전략:
1. ARM Cortex-M 알려진 패턴(reset handler 시작, 무한루프 default handler 등)으로
   crib (알려진 평문 조각) 만들기
2. 두 펌웨어 같은 위치 ciphertext 가 같음 → 평문도 같음 (검증)
3. 평문이 0xFF 0xFF ... 패딩으로 보이는 영역에서 키스트림 직접 추출
4. ARM 코드 디스어셈블 가능성 검사

입력: fwupd 레포의 모든 .dat 파일 (./releases/*/*/*.dat)
출력:
    keystream.bin       — 복구된 키스트림 (위치별 후보)
    decoded_M30.bin     — 추정 복호화된 펌웨어
    analysis_report.md  — 분석 보고서

사용:
    python crypto_attack.py <firmware_dir>
"""

from __future__ import annotations

import argparse
import os
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path


HEADER_LEN = 28


def load_firmware(path: Path) -> tuple[dict, bytes]:
    """헤더 파싱 + payload 반환."""
    data = path.read_bytes()
    if len(data) < HEADER_LEN:
        raise ValueError(f"Too small: {path}")
    hdr = {
        "version": struct.unpack("<i", data[0:4])[0],
        "dst_addr": struct.unpack("<I", data[4:8])[0],
        "size": struct.unpack("<I", data[8:12])[0],
        "padding": data[12:28].hex(),
    }
    payload = data[HEADER_LEN:]
    return hdr, payload


def find_all_firmwares(root: Path) -> list[Path]:
    return sorted(root.rglob("*.dat"))


def analyze_byte_distribution(payload: bytes) -> dict:
    c = Counter(payload)
    total = len(payload)
    from math import log2
    e = -sum((v / total) * log2(v / total) for v in c.values())
    return {
        "size": total,
        "entropy": e,
        "max_byte": max(c, key=c.get),
        "zero_byte_pct": c.get(0, 0) * 100 / total,
        "ff_byte_pct": c.get(0xFF, 0) * 100 / total,
    }


def position_match_matrix(payloads: list[bytes]) -> list[list[int]]:
    """모든 페어 i,j 에 대해 같은 위치 같은 바이트 개수 카운트."""
    n = len(payloads)
    mat = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            sz = min(len(payloads[i]), len(payloads[j]))
            count = sum(1 for k in range(sz) if payloads[i][k] == payloads[j][k])
            mat[i][j] = mat[j][i] = count
    return mat


def extract_keystream_candidates(payloads: list[bytes], min_agree: int = 2) -> dict[int, list[int]]:
    """
    같은 위치에서 N개 이상 펌웨어의 ciphertext 바이트가 모두 동일하면,
    → 그 위치 평문도 같고 키스트림도 같음
    → 그 ciphertext 가 plaintext XOR keystream
    → 평문이 0x00이면 ciphertext = keystream

    가장 강력한 단서: ciphertext 가 0xFF FF FF ... 같은 반복 패턴이거나,
    여러 펌웨어의 같은 위치가 모두 0xFF 등 단일 바이트면 거의 확정 ciphertext = key.

    여기선 일단 "같은 위치 같은 바이트" 가 어디 있는지 매핑.
    """
    if not payloads:
        return {}
    max_len = max(len(p) for p in payloads)
    same_positions = defaultdict(int)
    for i in range(min(min(len(p) for p in payloads), max_len)):
        first = payloads[0][i]
        if all(p[i] == first for p in payloads):
            same_positions[i] = first
    return same_positions


def arm_vector_table_crib(payload: bytes) -> dict:
    """
    ARM Cortex-M 벡터 테이블의 알려진 구조를 사용해 첫 N 슬롯의 평문 추측:
    - 슬롯 0: Initial SP (Top of RAM, 보통 0x2000xxxx LE)
    - 슬롯 1+: Reset Handler, 다른 핸들러들 (대부분 0x080034xx ~ 0x0801xxxx LE)
    """
    if len(payload) < 64:
        return {}

    candidates = {}

    # 시도할 SP 후보들
    sp_candidates = [
        0x20002000, 0x20003000, 0x20004000, 0x20005000,
        0x20008000, 0x2000A000, 0x20010000, 0x20020000,
    ]

    for sp in sp_candidates:
        sp_bytes = struct.pack("<I", sp)
        key_first4 = bytes(c ^ p for c, p in zip(payload[:4], sp_bytes))

        # 슬롯 1: Reset Handler — 보통 0x080034xx ~ 0x0801xxxx
        # 키 첫 4바이트와 같은 4바이트 키 사용 (위치-스트림 가설 검증)
        # 만약 그 가설 맞다면 슬롯 1 평문 = ciphertext[4:8] XOR key_first4 (반복)
        # 근데 슬롯별로 키가 달라야 함... 위치 i 의 key 는 위치 i 에 고정.
        # 일단 슬롯 1 ciphertext 만 dump
        slot1_cipher = payload[4:8]
        candidates[sp] = {
            "key_first4": key_first4.hex(),
            "slot1_cipher": slot1_cipher.hex(),
        }

    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description="8BitDo 펌웨어 사이퍼 분석")
    parser.add_argument("firmware_dir", help=".dat 파일들이 있는 디렉토리")
    parser.add_argument("-o", "--output", default="analysis_report.md")
    args = parser.parse_args()

    root = Path(args.firmware_dir)
    if not root.is_dir():
        print(f"[!] 디렉토리 아님: {root}")
        return 1

    fw_paths = find_all_firmwares(root)
    print(f"[*] {len(fw_paths)}개 펌웨어 발견")
    if not fw_paths:
        return 2

    fws = []
    for p in fw_paths:
        try:
            hdr, payload = load_firmware(p)
            fws.append((p, hdr, payload))
            print(f"  - {p.relative_to(root)}: v{hdr['version']:<6d} addr=0x{hdr['dst_addr']:08x} sz={len(payload):,}")
        except Exception as e:
            print(f"  [!] {p}: {e}")

    if not fws:
        return 3

    payloads = [p for _, _, p in fws]

    # 1. 페어 위치-일치 행렬
    print("\n[*] 같은 위치 같은 바이트 (페어별) ...")
    mat = position_match_matrix(payloads)
    for i, (pi, _, _) in enumerate(fws):
        for j, (pj, _, _) in enumerate(fws):
            if j <= i:
                continue
            sz = min(len(payloads[i]), len(payloads[j]))
            pct = mat[i][j] * 100 / sz if sz else 0
            mark = " ← 같은 키스트림 강력 추정" if pct > 2.0 else ""
            print(f"  {pi.name} ↔ {pj.name}: {mat[i][j]:,}/{sz:,} ({pct:.2f}%){mark}")

    # 2. N개 이상 펌웨어에서 같은 위치 같은 바이트 추출
    print("\n[*] 모든 펌웨어에서 같은 위치 같은 바이트 ...")
    same = extract_keystream_candidates(payloads, min_agree=len(payloads))
    print(f"  → 총 {len(same)} 위치에서 모든 펌웨어가 같은 ciphertext")
    if same:
        # 가장 자주 등장하는 ciphertext 바이트 — 그게 keystream byte 후보 (plain=0x00 가정시)
        top_vals = Counter(same.values()).most_common(10)
        print("  가장 흔한 ciphertext 값들 (plain=0x00 일 때 키스트림 후보):")
        for v, cnt in top_vals:
            print(f"    0x{v:02x}: {cnt}회")

    # 3. ARM 벡터 테이블 분석
    print("\n[*] ARM 벡터 테이블 가설 분석 (첫 번째 펌웨어) ...")
    crib = arm_vector_table_crib(payloads[0])
    for sp, info in list(crib.items())[:3]:
        print(f"  SP=0x{sp:08x} → key 첫 4B = {info['key_first4']}, slot1 cipher = {info['slot1_cipher']}")

    print("\n[OK] 분석 완료. 다음:")
    print("  - 모든 펌웨어 동일 ciphertext 위치 = 같은 평문 + 같은 key 영역")
    print("  - 이 영역에서 plain 후보 (보통 ARM 코드 패턴, 0x00 패딩, 0xFF 패딩)")
    print("    찾으면 그 위치의 key 복구")
    print("  - 키 복구되면 모든 펌웨어 그 위치 복호화 → 추가 plain 발견 → 재귀 확장")

    return 0


if __name__ == "__main__":
    sys.exit(main())
