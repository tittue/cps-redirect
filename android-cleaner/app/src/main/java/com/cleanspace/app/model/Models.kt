package com.cleanspace.app.model

import java.io.File

/** 정리 카테고리 */
enum class CleanCategory(val label: String, val emoji: String) {
    LARGE_FILES("큰 파일 (50MB+)", "📦"),
    DUPLICATES("중복 파일", "🔁"),
    SCREENSHOTS("스크린샷", "📸"),
    DOWNLOADS("다운로드", "⬇️"),
    APK_FILES("설치파일 (APK)", "📲"),
    EMPTY_FOLDERS("빈 폴더", "📂"),
    TEMP_FILES("임시/캐시 파일", "🗑️"),
}

/** 미디어 타입 — 저장공간 분석용 분류 */
enum class MediaType(val label: String, val emoji: String) {
    IMAGE("사진", "🖼️"),
    VIDEO("동영상", "🎬"),
    AUDIO("오디오", "🎵"),
    DOCUMENT("문서", "📄"),
    ARCHIVE("압축파일", "🗜️"),
    APK("설치파일", "📲"),
    OTHER("기타", "📁");

    companion object {
        fun fromExtension(name: String): MediaType {
            val ext = name.substringAfterLast('.', "").lowercase()
            return when (ext) {
                "jpg", "jpeg", "png", "gif", "webp", "bmp", "heic", "heif", "dng" -> IMAGE
                "mp4", "mkv", "avi", "mov", "webm", "3gp", "flv", "wmv", "m4v" -> VIDEO
                "mp3", "wav", "flac", "aac", "ogg", "m4a", "opus", "wma" -> AUDIO
                "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "hwp", "csv" -> DOCUMENT
                "zip", "rar", "7z", "tar", "gz", "bz2" -> ARCHIVE
                "apk", "xapk", "apks", "obb" -> APK
                else -> OTHER
            }
        }
    }
}

/** 스캔된 파일 항목 */
data class FileItem(
    val file: File,
    val sizeBytes: Long,
    val category: CleanCategory,
    var selected: Boolean = false,
    val duplicateGroupId: Int? = null,
) {
    val name: String get() = file.name
    val path: String get() = file.absolutePath
    val readableSize: String get() = formatSize(sizeBytes)
}

/** 카테고리별 정리 결과 */
data class CategoryResult(
    val category: CleanCategory,
    val items: List<FileItem>,
) {
    val totalSize: Long get() = items.sumOf { it.sizeBytes }
    val count: Int get() = items.size
    val readableSize: String get() = formatSize(totalSize)
}

/** 폴더 용량 노드 — "어디가 용량 먹는지" 분석용 */
data class FolderNode(
    val path: String,
    val name: String,
    val sizeBytes: Long,
    val fileCount: Int,
) {
    val readableSize: String get() = formatSize(sizeBytes)
}

/** 미디어 타입별 용량 집계 */
data class MediaBreakdown(
    val type: MediaType,
    val sizeBytes: Long,
    val count: Int,
) {
    val readableSize: String get() = formatSize(sizeBytes)
}

/** 설치된 앱의 용량 정보 (StorageStatsManager 기반) */
data class AppInfo(
    val packageName: String,
    val label: String,
    val appBytes: Long,
    val dataBytes: Long,
    val cacheBytes: Long,
    val isSystem: Boolean,
) {
    val totalBytes: Long get() = appBytes + dataBytes + cacheBytes
    val readableTotal: String get() = formatSize(totalBytes)
    val readableApp: String get() = formatSize(appBytes)
    val readableData: String get() = formatSize(dataBytes)
    val readableCache: String get() = formatSize(cacheBytes)
}

/** 저장공간 정보 */
data class StorageInfo(
    val totalBytes: Long,
    val freeBytes: Long,
) {
    val usedBytes: Long get() = totalBytes - freeBytes
    val usedPercent: Int get() = if (totalBytes > 0) ((usedBytes * 100) / totalBytes).toInt() else 0
    val readableTotal: String get() = formatSize(totalBytes)
    val readableFree: String get() = formatSize(freeBytes)
    val readableUsed: String get() = formatSize(usedBytes)
}

fun formatSize(bytes: Long): String {
    if (bytes < 1024) return "$bytes B"
    val kb = bytes / 1024.0
    if (kb < 1024) return "%.1f KB".format(kb)
    val mb = kb / 1024.0
    if (mb < 1024) return "%.1f MB".format(mb)
    val gb = mb / 1024.0
    return "%.2f GB".format(gb)
}
