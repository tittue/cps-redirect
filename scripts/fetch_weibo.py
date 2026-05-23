"""
Weibo 최신 영상 100건 fetcher

m.weibo.cn 의 공개 모바일 API에서 영상 게시물을 긁어와서
weibo/data.json 으로 저장한다. GitHub Actions cron 으로 주기 실행.

여러 containerid를 fallback으로 시도해서 차단/변경에 대비.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

import requests


# 시도할 컨테이너 ID들 (실시간/최신 영상 우선)
# 102803_ctg1_8999  = 视频
# 100103type=64     = 视频 검색
# 231643            = TV/video 탭
# 102803_ctg1_4188  = 推荐 (영상 포함)
CONTAINER_IDS = [
    "102803_ctg1_8999_-_ctg1_8999_home",  # 视频 카테고리 home
    "102803_ctg1_8999_-_ctg1_8999_realtime",  # 视频 실시간
    "231643",  # TV
    "102803_ctg1_4188_-_ctg1_4188_realtime",  # 핫 실시간
    "102803",  # 일반 핫
]

API_BASE = "https://m.weibo.cn/api/container/getIndex"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 "
        "Mobile/15E148 Safari/604.1"
    ),
    "Referer": "https://m.weibo.cn/",
    "Accept": "application/json, text/plain, */*",
    "MWeibo-Pwa": "1",
    "X-Requested-With": "XMLHttpRequest",
}

TARGET_COUNT = 100
TIMEOUT = 15


def strip_html(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s).strip()


def parse_time(s: str | None) -> str | None:
    """웨이보 시간 문자열을 ISO 형식으로 정규화."""
    if not s:
        return None
    try:
        # 'Sun Dec 17 12:34:56 +0800 2023' 같은 RFC2822 변형
        d = dt.datetime.strptime(s, "%a %b %d %H:%M:%S %z %Y")
        return d.astimezone(dt.timezone.utc).isoformat()
    except (ValueError, TypeError):
        return s


def extract_video(mblog: dict) -> dict | None:
    """mblog 객체에서 영상 정보가 있으면 정규화된 dict 반환, 없으면 None."""
    if not isinstance(mblog, dict):
        return None

    # 영상 후보 필드들
    page_info = mblog.get("page_info") or {}
    object_type = page_info.get("object_type", "")
    type_name = page_info.get("type", "")

    is_video = (
        object_type == "video"
        or type_name == "video"
        or "media_info" in page_info
        or "video" in (page_info.get("urls") or {})
    )
    if not is_video:
        return None

    media_info = page_info.get("media_info") or {}
    user = mblog.get("user") or {}

    # 썸네일
    thumb = (
        page_info.get("page_pic", {}).get("url")
        if isinstance(page_info.get("page_pic"), dict)
        else page_info.get("page_pic")
    )
    if not thumb:
        thumb = mblog.get("bmiddle_pic") or mblog.get("thumbnail_pic")

    # 영상 URL
    video_url = (
        media_info.get("stream_url_hd")
        or media_info.get("stream_url")
        or media_info.get("h5_url")
        or (page_info.get("urls") or {}).get("mp4_hd_mp4")
        or (page_info.get("urls") or {}).get("mp4_720p_mp4")
        or (page_info.get("urls") or {}).get("mp4_ld_mp4")
    )

    bid = mblog.get("bid") or mblog.get("id")
    page_url = (
        f"https://m.weibo.cn/status/{bid}" if bid else page_info.get("page_url", "")
    )

    return {
        "id": str(mblog.get("id", "")),
        "bid": bid,
        "title": strip_html(
            page_info.get("title")
            or media_info.get("name")
            or mblog.get("text", "")
        )[:200],
        "text": strip_html(mblog.get("text", ""))[:500],
        "author": {
            "name": user.get("screen_name", ""),
            "id": user.get("id"),
            "avatar": user.get("profile_image_url", ""),
            "verified": bool(user.get("verified", False)),
        },
        "thumbnail": thumb,
        "video_url": video_url,
        "page_url": page_url,
        "duration": media_info.get("duration"),
        "play_count": page_info.get("play_count") or media_info.get("online_users"),
        "reposts": mblog.get("reposts_count", 0),
        "comments": mblog.get("comments_count", 0),
        "attitudes": mblog.get("attitudes_count", 0),
        "created_at": parse_time(mblog.get("created_at")),
        "source": strip_html(mblog.get("source", "")),
    }


def fetch_container(session: requests.Session, container_id: str, page: int = 1) -> list[dict]:
    """단일 컨테이너에서 1페이지를 받아 영상만 추출."""
    params = {
        "containerid": container_id,
        "page": page,
        "count": 50,
    }
    try:
        r = session.get(API_BASE, params=params, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError) as e:
        print(f"  ! container {container_id} page {page} 실패: {e}", file=sys.stderr)
        return []

    if data.get("ok") != 1:
        return []

    cards = (data.get("data") or {}).get("cards") or []
    videos: list[dict] = []
    for card in cards:
        # card_group 안에도 mblog가 있을 수 있음
        candidates = []
        if "mblog" in card:
            candidates.append(card["mblog"])
        for sub in card.get("card_group", []) or []:
            if "mblog" in sub:
                candidates.append(sub["mblog"])

        for mblog in candidates:
            video = extract_video(mblog)
            if video:
                videos.append(video)

    return videos


def fetch_all() -> list[dict]:
    session = requests.Session()
    all_videos: dict[str, dict] = {}

    for container_id in CONTAINER_IDS:
        print(f"  - container: {container_id}")
        for page in range(1, 6):  # 최대 5페이지까지
            videos = fetch_container(session, container_id, page)
            if not videos:
                break
            new_count = 0
            for v in videos:
                key = v["id"] or v.get("bid") or v.get("page_url")
                if key and key not in all_videos:
                    all_videos[key] = v
                    new_count += 1
            print(f"    page {page}: +{new_count} (총 {len(all_videos)})")
            if len(all_videos) >= TARGET_COUNT:
                break
        if len(all_videos) >= TARGET_COUNT:
            break

    # 시간순 정렬 (최신 우선), 정렬 가능한 것만
    videos = list(all_videos.values())
    videos.sort(
        key=lambda v: v.get("created_at") or "",
        reverse=True,
    )
    return videos[:TARGET_COUNT]


def main() -> int:
    print("[Weibo Fetcher] 시작")
    videos = fetch_all()
    print(f"[Weibo Fetcher] 총 {len(videos)}개 영상 수집됨")

    output = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "count": len(videos),
        "videos": videos,
    }

    repo_root = Path(__file__).resolve().parent.parent
    out_path = repo_root / "weibo" / "data.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[Weibo Fetcher] 저장: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
