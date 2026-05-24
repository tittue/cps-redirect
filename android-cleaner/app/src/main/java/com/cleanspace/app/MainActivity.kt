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

    private val legacyPermLauncher =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {
            hasPermission = checkStoragePermission()
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        hasPermission = checkStoragePermission()

        setContent {
            CleanSpaceTheme {
                if (hasPermission) {
                    val vm: CleanViewModel = viewModel()
                    MainScreen(vm)
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
            // MANAGE_EXTERNAL_STORAGE — 설정 화면으로 이동
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
}
