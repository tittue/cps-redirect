package com.cleanspace.app.scanner

import android.os.Environment
import android.os.StatFs
import com.cleanspace.app.model.CategoryResult
import com.cleanspace.app.model.CleanCategory
import com.cleanspace.app.model.FileItem
import com.cleanspace.app.model.FolderNode
import com.cleanspace.app.model.MediaBreakdown
import com.cleanspace.app.model.MediaType
import com.cleanspace.app.model.StorageInfo
import java.io.File
import java.security.MessageDigest

/**
 * 저장공간 스캐너 — 전체 외부 저장소를 한 번 순회하면서:
 *  - 폴더별 용량 집계 (어디가 용량 먹는지)
 *  - 미디어 타입별 집계 (사진/영상/...)
 *  - 정리 카테고리별 파일 수집 (큰 파일/스크린샷/APK/...)
 *  - 중복 후보 (크기 같은 파일 → 해시 비교)
 *
 * MANAGE_EXTERNAL_STORAGE 권한 하에 동작.
 */
class StorageScanner(
    private val root: File = Environment.getExternalStorageDirectory(),
) {
    var onProgress: ((scanned: Int, currentPath: String) -> Unit)? = null

    private val largeThreshold = 50L * 1024 * 1024  // 50MB

    // 결과 누적
    private val folderSizes = HashMap<String, LongArray>()  // path -> [size, count]
    private val mediaSizes = HashMap<MediaType, LongArray>() // type -> [size, count]
    private val largeFiles = ArrayList<FileItem>()
    private val screenshots = ArrayList<FileItem>()
    private val downloads = ArrayList<FileItem>()
    private val apks = ArrayList<FileItem>()
    private val emptyFolders = ArrayList<FileItem>()
    private val tempFiles = ArrayList<FileItem>()
    private val bySize = HashMap<Long, MutableList<File>>()  // 중복 후보
    private var scannedCount = 0

    fun getStorageInfo(): StorageInfo {
        val stat = StatFs(root.absolutePath)
        val total = stat.totalBytes
        val free = stat.availableBytes
        return StorageInfo(totalBytes = total, freeBytes = free)
    }

    /** 전체 스캔 실행. 한 번의 깊이우선 순회. */
    fun scan(): ScanResult {
        walk(root, depth = 0)

        // 중복: 크기가 같은 그룹만 해시 비교
        val duplicates = ArrayList<FileItem>()
        var groupId = 0
        for ((size, files) in bySize) {
            if (files.size < 2 || size < 1024) continue  // 1KB 미만 무시
            val byHash = HashMap<String, MutableList<File>>()
            for (f in files) {
                val h = quickHash(f) ?: continue
                byHash.getOrPut(h) { ArrayList() }.add(f)
            }
            for ((_, group) in byHash) {
                if (group.size < 2) continue
                groupId++
                // 첫 번째는 원본으로 두고 나머지를 중복으로 표시 (선택은 사용자가)
                group.forEachIndexed { idx, f ->
                    duplicates.add(
                        FileItem(
                            file = f,
                            sizeBytes = size,
                            category = CleanCategory.DUPLICATES,
                            selected = idx > 0,  // 두 번째부터 기본 선택
                            duplicateGroupId = groupId,
                        )
                    )
                }
            }
        }

        // 폴더 용량 top 30
        val topFolders = folderSizes.entries
            .map { (path, arr) ->
                FolderNode(
                    path = path,
                    name = File(path).name.ifEmpty { path },
                    sizeBytes = arr[0],
                    fileCount = arr[1].toInt(),
                )
            }
            .sortedByDescending { it.sizeBytes }
            .take(30)

        // 미디어 타입별
        val mediaBreakdown = mediaSizes.entries
            .map { (type, arr) -> MediaBreakdown(type, arr[0], arr[1].toInt()) }
            .sortedByDescending { it.sizeBytes }

        val categories = listOf(
            CategoryResult(CleanCategory.LARGE_FILES, largeFiles.sortedByDescending { it.sizeBytes }),
            CategoryResult(CleanCategory.DUPLICATES, duplicates),
            CategoryResult(CleanCategory.SCREENSHOTS, screenshots.sortedByDescending { it.sizeBytes }),
            CategoryResult(CleanCategory.DOWNLOADS, downloads.sortedByDescending { it.sizeBytes }),
            CategoryResult(CleanCategory.APK_FILES, apks.sortedByDescending { it.sizeBytes }),
            CategoryResult(CleanCategory.TEMP_FILES, tempFiles.sortedByDescending { it.sizeBytes }),
            CategoryResult(CleanCategory.EMPTY_FOLDERS, emptyFolders),
        )

        return ScanResult(
            storage = getStorageInfo(),
            topFolders = topFolders,
            mediaBreakdown = mediaBreakdown,
            categories = categories,
            totalScanned = scannedCount,
        )
    }

    /** 깊이우선 순회. 폴더 크기는 하위 전체 합산. 반환값 = 이 폴더의 총 바이트. */
    private fun walk(dir: File, depth: Int): Long {
        val children = dir.listFiles() ?: return 0L
        if (children.isEmpty() && depth > 0) {
            emptyFolders.add(FileItem(dir, 0, CleanCategory.EMPTY_FOLDERS))
            return 0L
        }

        var dirTotal = 0L
        var dirCount = 0
        val lowerPath = dir.absolutePath.lowercase()

        for (child in children) {
            // 심볼릭 링크/특수 경로 회피
            if (child.name.startsWith(".")) {
                // 숨김 파일도 크기엔 포함하되 카테고리엔 제외
            }
            if (child.isDirectory) {
                val sub = walk(child, depth + 1)
                dirTotal += sub
            } else {
                val size = child.length()
                dirTotal += size
                dirCount++
                scannedCount++
                if (scannedCount % 200 == 0) {
                    onProgress?.invoke(scannedCount, child.absolutePath)
                }
                classify(child, size, lowerPath)
            }
        }

        // 이 폴더(직속만 아니라 하위 포함)를 폴더 용량 맵에 기록
        if (dirTotal > 0) {
            folderSizes[dir.absolutePath] = longArrayOf(dirTotal, dirCount.toLong())
        }
        return dirTotal
    }

    private fun classify(file: File, size: Long, parentLower: String) {
        val name = file.name
        val nameLower = name.lowercase()

        // 미디어 타입 집계
        val mtype = MediaType.fromExtension(name)
        val arr = mediaSizes.getOrPut(mtype) { longArrayOf(0, 0) }
        arr[0] += size
        arr[1] += 1

        // 중복 후보 (크기 기준 그룹)
        bySize.getOrPut(size) { ArrayList() }.add(file)

        // 큰 파일
        if (size >= largeThreshold) {
            largeFiles.add(FileItem(file, size, CleanCategory.LARGE_FILES))
        }

        // 스크린샷 (경로 또는 이름)
        if ("screenshot" in parentLower || "screenshots" in parentLower ||
            nameLower.startsWith("screenshot") || nameLower.startsWith("스크린샷")
        ) {
            screenshots.add(FileItem(file, size, CleanCategory.SCREENSHOTS))
        }

        // 다운로드 폴더
        if (parentLower.endsWith("/download") || parentLower.endsWith("/downloads") ||
            "/download/" in parentLower || "/downloads/" in parentLower
        ) {
            downloads.add(FileItem(file, size, CleanCategory.DOWNLOADS))
        }

        // APK 설치파일
        if (mtype == MediaType.APK) {
            apks.add(FileItem(file, size, CleanCategory.APK_FILES))
        }

        // 임시/캐시 파일
        if (nameLower.endsWith(".tmp") || nameLower.endsWith(".temp") ||
            nameLower.endsWith(".log") || nameLower.endsWith(".crdownload") ||
            nameLower.endsWith(".part") || "/cache/" in parentLower ||
            "/.thumbnails/" in parentLower
        ) {
            tempFiles.add(FileItem(file, size, CleanCategory.TEMP_FILES))
        }
    }

    /** 빠른 해시: 처음 + 끝 64KB만 (전체 해시는 너무 느림) */
    private fun quickHash(file: File): String? {
        return try {
            val md = MessageDigest.getInstance("MD5")
            file.inputStream().use { input ->
                val buf = ByteArray(64 * 1024)
                val read = input.read(buf)
                if (read > 0) md.update(buf, 0, read)
                // 끝부분
                if (file.length() > 128 * 1024) {
                    file.inputStream().use { tail ->
                        tail.skip(file.length() - 64 * 1024)
                        val r2 = tail.read(buf)
                        if (r2 > 0) md.update(buf, 0, r2)
                    }
                }
            }
            md.update(file.length().toString().toByteArray())
            md.digest().joinToString("") { "%02x".format(it) }
        } catch (e: Exception) {
            null
        }
    }
}

data class ScanResult(
    val storage: StorageInfo,
    val topFolders: List<FolderNode>,
    val mediaBreakdown: List<MediaBreakdown>,
    val categories: List<CategoryResult>,
    val totalScanned: Int,
)
