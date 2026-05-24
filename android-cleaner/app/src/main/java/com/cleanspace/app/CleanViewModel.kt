package com.cleanspace.app

import android.content.Context
import android.os.Environment
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.cleanspace.app.model.AppInfo
import com.cleanspace.app.model.CategoryResult
import com.cleanspace.app.model.CleanCategory
import com.cleanspace.app.model.FileItem
import com.cleanspace.app.scanner.AppScanner
import com.cleanspace.app.scanner.ScanResult
import com.cleanspace.app.scanner.StorageScanner
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

sealed interface ScanState {
    data object Idle : ScanState
    data class Scanning(val count: Int, val path: String) : ScanState
    data class Done(val result: ScanResult) : ScanState
    data class Error(val message: String) : ScanState
}

sealed interface AppScanState {
    data object Idle : AppScanState
    data object Scanning : AppScanState
    data object NoPermission : AppScanState
    data class Done(val apps: List<AppInfo>) : AppScanState
}

class CleanViewModel : ViewModel() {
    var scanState by mutableStateOf<ScanState>(ScanState.Idle)
        private set

    var appScanState by mutableStateOf<AppScanState>(AppScanState.Idle)
        private set

    private val selectedPackages = mutableSetOf<String>()

    fun scanApps(context: Context) {
        appScanState = AppScanState.Scanning
        viewModelScope.launch {
            val scanner = AppScanner(context.applicationContext)
            if (!scanner.hasUsageAccess()) {
                appScanState = AppScanState.NoPermission
                return@launch
            }
            val apps = withContext(Dispatchers.IO) { scanner.scan(includeSystem = false) }
            selectedPackages.clear()
            appScanState = AppScanState.Done(apps)
        }
    }

    fun isAppSelected(pkg: String): Boolean = selectedPackages.contains(pkg)

    fun toggleApp(pkg: String) {
        if (selectedPackages.contains(pkg)) selectedPackages.remove(pkg)
        else selectedPackages.add(pkg)
        val s = appScanState
        if (s is AppScanState.Done) appScanState = AppScanState.Done(s.apps)
    }

    fun selectedAppPackages(): List<String> = selectedPackages.toList()

    fun selectedAppCount(): Int = selectedPackages.size

    fun selectedAppBytes(): Long {
        val s = appScanState as? AppScanState.Done ?: return 0L
        return s.apps.filter { selectedPackages.contains(it.packageName) }.sumOf { it.totalBytes }
    }

    fun clearAppSelection() {
        selectedPackages.clear()
        val s = appScanState
        if (s is AppScanState.Done) appScanState = AppScanState.Done(s.apps)
    }

    // 선택 상태를 path 기준으로 별도 관리 (재구성에도 유지)
    private val selectedPaths = mutableSetOf<String>()

    var lastDeletedBytes by mutableStateOf(0L)
        private set

    fun startScan() {
        scanState = ScanState.Scanning(0, "")
        viewModelScope.launch {
            try {
                val result = withContext(Dispatchers.IO) {
                    val scanner = StorageScanner(Environment.getExternalStorageDirectory())
                    scanner.onProgress = { count, path ->
                        scanState = ScanState.Scanning(count, path)
                    }
                    scanner.scan()
                }
                // 중복 기본 선택 반영
                selectedPaths.clear()
                result.categories.find { it.category == CleanCategory.DUPLICATES }
                    ?.items?.filter { it.selected }?.forEach { selectedPaths.add(it.path) }
                scanState = ScanState.Done(result)
            } catch (e: Exception) {
                scanState = ScanState.Error(e.message ?: "스캔 실패")
            }
        }
    }

    fun isSelected(item: FileItem): Boolean = selectedPaths.contains(item.path)

    fun toggleSelect(item: FileItem) {
        if (selectedPaths.contains(item.path)) selectedPaths.remove(item.path)
        else selectedPaths.add(item.path)
        // 트리거 재구성
        val s = scanState
        if (s is ScanState.Done) scanState = ScanState.Done(s.result)
    }

    fun selectAll(category: CategoryResult, select: Boolean) {
        category.items.forEach {
            if (select) selectedPaths.add(it.path) else selectedPaths.remove(it.path)
        }
        val s = scanState
        if (s is ScanState.Done) scanState = ScanState.Done(s.result)
    }

    fun selectedCount(): Int = selectedPaths.size

    fun selectedBytes(): Long {
        val s = scanState as? ScanState.Done ?: return 0L
        return s.result.categories.flatMap { it.items }
            .filter { selectedPaths.contains(it.path) }
            .distinctBy { it.path }
            .sumOf { it.sizeBytes }
    }

    /** 선택된 파일 일괄 삭제. 삭제된 바이트 반환. */
    fun deleteSelected(onComplete: (deletedBytes: Long, deletedCount: Int, failed: Int) -> Unit) {
        val s = scanState as? ScanState.Done ?: return
        viewModelScope.launch {
            val (bytes, count, failed) = withContext(Dispatchers.IO) {
                var b = 0L; var c = 0; var f = 0
                val targets = s.result.categories.flatMap { it.items }
                    .filter { selectedPaths.contains(it.path) }
                    .distinctBy { it.path }
                for (item in targets) {
                    val sz = item.sizeBytes
                    if (item.file.exists() && item.file.delete()) {
                        b += sz; c++
                    } else {
                        f++
                    }
                }
                Triple(b, c, f)
            }
            lastDeletedBytes = bytes
            selectedPaths.clear()
            onComplete(bytes, count, failed)
            // 재스캔으로 갱신
            startScan()
        }
    }
}
