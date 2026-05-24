package com.cleanspace.app.scanner

import android.app.AppOpsManager
import android.app.usage.StorageStatsManager
import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.os.Process
import android.os.storage.StorageManager
import com.cleanspace.app.model.AppInfo

/**
 * 설치된 앱들의 용량을 StorageStatsManager 로 조회.
 * PACKAGE_USAGE_STATS (사용 정보 접근) 권한 필요.
 */
class AppScanner(private val context: Context) {

    fun hasUsageAccess(): Boolean {
        return try {
            val appOps = context.getSystemService(Context.APP_OPS_SERVICE) as AppOpsManager
            val mode = appOps.checkOpNoThrow(
                AppOpsManager.OPSTR_GET_USAGE_STATS,
                Process.myUid(),
                context.packageName,
            )
            mode == AppOpsManager.MODE_ALLOWED
        } catch (e: Exception) {
            false
        }
    }

    fun scan(includeSystem: Boolean = false): List<AppInfo> {
        val pm = context.packageManager
        val ssm = context.getSystemService(Context.STORAGE_STATS_SERVICE) as StorageStatsManager
        val user = Process.myUserHandle()
        val uuid = StorageManager.UUID_DEFAULT

        val installed = pm.getInstalledApplications(PackageManager.GET_META_DATA)
        val result = ArrayList<AppInfo>(installed.size)

        for (app in installed) {
            val isSystem = (app.flags and ApplicationInfo.FLAG_SYSTEM) != 0
            if (isSystem && !includeSystem) continue
            try {
                val stats = ssm.queryStatsForPackage(uuid, app.packageName, user)
                val label = pm.getApplicationLabel(app).toString()
                result.add(
                    AppInfo(
                        packageName = app.packageName,
                        label = label,
                        appBytes = stats.appBytes,
                        dataBytes = stats.dataBytes,
                        cacheBytes = stats.cacheBytes,
                        isSystem = isSystem,
                    )
                )
            } catch (e: Exception) {
                // 권한 없거나 일부 앱 조회 실패 → skip
            }
        }
        return result.sortedByDescending { it.totalBytes }
    }
}
