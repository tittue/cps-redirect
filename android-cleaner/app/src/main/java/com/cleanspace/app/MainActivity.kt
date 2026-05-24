package com.cleanspace.app

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.viewmodel.compose.viewModel
import com.cleanspace.app.ui.CleanSpaceTheme
import com.cleanspace.app.ui.MainScreen
import com.cleanspace.app.ui.PermissionScreen

class MainActivity : ComponentActivity() {

    private var hasPermission by mutableStateOf(false)

    // 순차 앱 제거 큐
    private val uninstallQueue = ArrayDeque<String>()
    private var onUninstallsDone: (() -> Unit)? = null

    private val legacyPermLauncher =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {
            hasPermission = checkStoragePermission()
        }

    private val uninstallLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) {
            launchNextUninstall()
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        hasPermission = checkStoragePermission()

        setContent {
            CleanSpaceTheme {
                if (hasPermission) {
                    val vm: CleanViewModel = viewModel()
                    MainScreen(
                        vm = vm,
                        onOpenUsageAccess = { openUsageAccessSettings() },
                        onUninstallApps = { pkgs, done -> startUninstalls(pkgs, done) },
                        onOpenAppInfo = { pkg -> openAppInfo(pkg) },
                    )
                } else {
                    PermissionScreen(onRequest = { requestStoragePermission() })
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        hasPermission = checkStoragePermission()
    }

    // ---- 저장소 권한 ----

    private fun checkStoragePermission(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            Environment.isExternalStorageManager()
        } else {
            checkSelfPermission(android.Manifest.permission.READ_EXTERNAL_STORAGE) ==
                android.content.pm.PackageManager.PERMISSION_GRANTED
        }
    }

    private fun requestStoragePermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            try {
                val intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                intent.data = Uri.parse("package:$packageName")
                startActivity(intent)
            } catch (e: Exception) {
                startActivity(Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION))
            }
        } else {
            legacyPermLauncher.launch(
                arrayOf(
                    android.Manifest.permission.READ_EXTERNAL_STORAGE,
                    android.Manifest.permission.WRITE_EXTERNAL_STORAGE,
                )
            )
        }
    }

    // ---- 사용 정보 접근 (앱별 용량용) ----

    private fun openUsageAccessSettings() {
        try {
            startActivity(Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS))
        } catch (e: Exception) {
            startActivity(Intent(Settings.ACTION_SETTINGS))
        }
    }

    private fun openAppInfo(pkg: String) {
        try {
            val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
            intent.data = Uri.parse("package:$pkg")
            startActivity(intent)
        } catch (e: Exception) {
            // ignore
        }
    }

    // ---- 순차 앱 제거 ----

    private fun startUninstalls(pkgs: List<String>, done: () -> Unit) {
        uninstallQueue.clear()
        uninstallQueue.addAll(pkgs)
        onUninstallsDone = done
        launchNextUninstall()
    }

    private fun launchNextUninstall() {
        val pkg = uninstallQueue.removeFirstOrNull()
        if (pkg == null) {
            onUninstallsDone?.invoke()
            onUninstallsDone = null
            return
        }
        try {
            @Suppress("DEPRECATION")
            val intent = Intent(Intent.ACTION_UNINSTALL_PACKAGE, Uri.parse("package:$pkg"))
            intent.putExtra(Intent.EXTRA_RETURN_RESULT, true)
            uninstallLauncher.launch(intent)
        } catch (e: Exception) {
            launchNextUninstall()
        }
    }
}
