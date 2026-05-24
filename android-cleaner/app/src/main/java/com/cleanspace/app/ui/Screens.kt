package com.cleanspace.app.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.cleanspace.app.AppScanState
import com.cleanspace.app.CleanViewModel
import com.cleanspace.app.ScanState
import com.cleanspace.app.model.*

@Composable
fun PermissionScreen(onRequest: () -> Unit) {
    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            modifier = Modifier.fillMaxSize().padding(28.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text("🧹", fontSize = 64.sp)
            Spacer(Modifier.height(16.dp))
            Text(
                "CleanSpace",
                fontSize = 28.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary,
            )
            Spacer(Modifier.height(8.dp))
            Text(
                "저장공간 분석 & 일괄 정리\n광고 없음",
                fontSize = 14.sp,
                color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.7f),
            )
            Spacer(Modifier.height(32.dp))
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant
                ),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column(Modifier.padding(18.dp)) {
                    Text("📂 전체 파일 접근 권한 필요", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                    Spacer(Modifier.height(8.dp))
                    Text(
                        "저장공간 전체를 분석해서 뭐가 용량을 차지하는지 보여주려면 '모든 파일 접근' 권한이 필요해요. " +
                            "다음 화면에서 토글을 켜주세요.",
                        fontSize = 13.sp,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.75f),
                    )
                }
            }
            Spacer(Modifier.height(24.dp))
            Button(
                onClick = onRequest,
                modifier = Modifier.fillMaxWidth().height(52.dp),
            ) {
                Text("권한 설정하러 가기", fontSize = 16.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    vm: CleanViewModel,
    onOpenUsageAccess: () -> Unit,
    onUninstallApps: (List<String>, () -> Unit) -> Unit,
    onOpenAppInfo: (String) -> Unit,
) {
    val context = LocalContext.current
    var tab by remember { mutableStateOf(0) }  // 0 = 파일, 1 = 앱
    val state = vm.scanState
    val appState = vm.appScanState

    LaunchedEffect(Unit) {
        if (state is ScanState.Idle) vm.startScan()
    }
    LaunchedEffect(tab) {
        if (tab == 1 && appState is AppScanState.Idle) vm.scanApps(context)
    }

    var snackbarMsg by remember { mutableStateOf<String?>(null) }
    val snackbarHost = remember { SnackbarHostState() }
    LaunchedEffect(snackbarMsg) {
        snackbarMsg?.let { snackbarHost.showSnackbar(it); snackbarMsg = null }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHost) },
        topBar = {
            Column {
                TopAppBar(
                    title = { Text("🧹 CleanSpace", fontWeight = FontWeight.Bold) },
                    actions = {
                        IconButton(onClick = {
                            if (tab == 0) vm.startScan() else vm.scanApps(context)
                        }) {
                            Icon(Icons.Default.Refresh, contentDescription = "다시 스캔")
                        }
                    },
                )
                TabRow(selectedTabIndex = tab) {
                    Tab(selected = tab == 0, onClick = { tab = 0 },
                        text = { Text("📁 파일 정리") })
                    Tab(selected = tab == 1, onClick = { tab = 1 },
                        text = { Text("📲 앱 용량") })
                }
            }
        },
        bottomBar = {
            if (tab == 0) {
                val selCount = vm.selectedCount()
                if (selCount > 0) {
                    DeleteBar(
                        count = selCount,
                        bytes = vm.selectedBytes(),
                        label = "삭제",
                        onDelete = {
                            vm.deleteSelected { bytes, count, failed ->
                                snackbarMsg = "✓ ${count}개 삭제 (${formatSize(bytes)} 확보)" +
                                    if (failed > 0) " · ${failed}개 실패" else ""
                            }
                        },
                    )
                }
            } else {
                val selCount = vm.selectedAppCount()
                if (selCount > 0) {
                    DeleteBar(
                        count = selCount,
                        bytes = vm.selectedAppBytes(),
                        label = "제거",
                        onDelete = {
                            val pkgs = vm.selectedAppPackages()
                            onUninstallApps(pkgs) {
                                vm.clearAppSelection()
                                vm.scanApps(context)
                            }
                        },
                    )
                }
            }
        },
    ) { padding ->
        val gradient = Brush.verticalGradient(
            listOf(
                MaterialTheme.colorScheme.secondary.copy(alpha = 0.10f),
                MaterialTheme.colorScheme.background,
            )
        )
        Box(
            Modifier.padding(padding).fillMaxSize().background(gradient)
        ) {
            if (tab == 0) {
                when (state) {
                    is ScanState.Idle -> {}
                    is ScanState.Scanning -> ScanningView(state)
                    is ScanState.Error -> ErrorView(state.message) { vm.startScan() }
                    is ScanState.Done -> ResultView(vm, state)
                }
            } else {
                AppsView(
                    state = appState,
                    isSelected = { vm.isAppSelected(it) },
                    onToggle = { vm.toggleApp(it) },
                    onOpenInfo = onOpenAppInfo,
                    onGrantPermission = onOpenUsageAccess,
                )
            }
        }
    }
}

@Composable
private fun AppsView(
    state: AppScanState,
    isSelected: (String) -> Boolean,
    onToggle: (String) -> Unit,
    onOpenInfo: (String) -> Unit,
    onGrantPermission: () -> Unit,
) {
    when (state) {
        is AppScanState.Idle, AppScanState.Scanning -> {
            Column(
                Modifier.fillMaxSize().padding(28.dp),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
                Spacer(Modifier.height(16.dp))
                Text("앱 용량 분석 중...", fontWeight = FontWeight.Bold)
            }
        }
        is AppScanState.NoPermission -> {
            Column(
                Modifier.fillMaxSize().padding(28.dp),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text("🔐", fontSize = 48.sp)
                Spacer(Modifier.height(12.dp))
                Text("'사용 정보 접근' 권한 필요", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                Spacer(Modifier.height(8.dp))
                Text(
                    "앱별 용량을 보려면 '사용 정보 접근' 권한이 필요해요. " +
                        "다음 화면에서 CleanSpace를 찾아 허용해주세요.",
                    fontSize = 13.sp,
                    color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.7f),
                )
                Spacer(Modifier.height(20.dp))
                Button(onClick = onGrantPermission) { Text("권한 설정하러 가기") }
            }
        }
        is AppScanState.Done -> {
            if (state.apps.isEmpty()) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("표시할 앱이 없습니다", color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.6f))
                }
                return
            }
            LazyColumn(
                Modifier.fillMaxSize(),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                item {
                    Text(
                        "용량 큰 순. 체크 후 '제거' 누르면 순서대로 제거창이 떠요. " +
                            "앱 탭 → 정보 화면(캐시/데이터 정리).",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.6f),
                        modifier = Modifier.padding(bottom = 4.dp),
                    )
                }
                items(state.apps) { app ->
                    AppRow(app, isSelected(app.packageName),
                        onToggle = { onToggle(app.packageName) },
                        onInfo = { onOpenInfo(app.packageName) })
                }
                item { Spacer(Modifier.height(80.dp)) }
            }
        }
    }
}

@Composable
private fun AppRow(
    app: com.cleanspace.app.model.AppInfo,
    selected: Boolean,
    onToggle: () -> Unit,
    onInfo: () -> Unit,
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Checkbox(checked = selected, onCheckedChange = { onToggle() })
            Column(Modifier.weight(1f).clickable { onToggle() }) {
                Text(app.label, fontSize = 14.sp, fontWeight = FontWeight.Medium,
                    maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text("앱 ${app.readableApp} · 데이터 ${app.readableData} · 캐시 ${app.readableCache}",
                    fontSize = 10.sp,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                    maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            Spacer(Modifier.width(8.dp))
            Text(app.readableTotal, fontWeight = FontWeight.Bold, fontSize = 14.sp,
                color = MaterialTheme.colorScheme.primary)
            IconButton(onClick = onInfo) {
                Icon(Icons.Default.Info, contentDescription = "앱 정보")
            }
        }
    }
}

@Composable
private fun ScanningView(state: ScanState.Scanning) {
    Column(
        Modifier.fillMaxSize().padding(28.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
        Spacer(Modifier.height(20.dp))
        Text("저장공간 스캔 중...", fontWeight = FontWeight.Bold, fontSize = 16.sp)
        Spacer(Modifier.height(6.dp))
        Text("${state.count}개 파일 분석함", fontSize = 13.sp,
            color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.6f))
        Spacer(Modifier.height(4.dp))
        Text(
            state.path.takeLast(40),
            fontSize = 10.sp,
            color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.4f),
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun ErrorView(msg: String, onRetry: () -> Unit) {
    Column(
        Modifier.fillMaxSize().padding(28.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text("⚠️", fontSize = 48.sp)
        Spacer(Modifier.height(12.dp))
        Text("스캔 실패", fontWeight = FontWeight.Bold)
        Text(msg, fontSize = 12.sp, color = MaterialTheme.colorScheme.error)
        Spacer(Modifier.height(16.dp))
        Button(onClick = onRetry) { Text("다시 시도") }
    }
}

@Composable
private fun ResultView(vm: CleanViewModel, state: ScanState.Done) {
    val result = state.result
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item { StorageCard(result.storage) }
        item { MediaBreakdownCard(result.mediaBreakdown) }
        item {
            SectionTitle("📊 용량 많이 먹는 폴더 TOP")
        }
        items(result.topFolders.take(15)) { folder ->
            FolderRow(folder, result.storage.usedBytes)
        }
        item { SectionTitle("🧹 정리하기") }
        items(result.categories.filter { it.count > 0 }) { cat ->
            CategoryCard(vm, cat)
        }
        item { Spacer(Modifier.height(80.dp)) }
    }
}

@Composable
private fun StorageCard(storage: StorageInfo) {
    val primary = MaterialTheme.colorScheme.primary
    val secondary = MaterialTheme.colorScheme.secondary
    val danger = MaterialTheme.colorScheme.error
    val track = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.08f)
    val arcColor = if (storage.usedPercent > 90) danger else primary

    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(22.dp),
    ) {
        Row(
            Modifier.fillMaxWidth().padding(20.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            // 도넛 차트
            Box(contentAlignment = Alignment.Center, modifier = Modifier.size(120.dp)) {
                Canvas(modifier = Modifier.size(120.dp)) {
                    val strokeW = 16.dp.toPx()
                    val inset = strokeW / 2
                    val arcSize = androidx.compose.ui.geometry.Size(
                        size.width - strokeW, size.height - strokeW
                    )
                    val topLeft = Offset(inset, inset)
                    drawArc(
                        color = track,
                        startAngle = -90f, sweepAngle = 360f, useCenter = false,
                        topLeft = topLeft, size = arcSize,
                        style = Stroke(width = strokeW, cap = StrokeCap.Round),
                    )
                    drawArc(
                        brush = Brush.sweepGradient(listOf(secondary, arcColor, arcColor)),
                        startAngle = -90f,
                        sweepAngle = 360f * (storage.usedPercent / 100f),
                        useCenter = false,
                        topLeft = topLeft, size = arcSize,
                        style = Stroke(width = strokeW, cap = StrokeCap.Round),
                    )
                }
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("${storage.usedPercent}%", fontSize = 26.sp, fontWeight = FontWeight.Bold,
                        color = arcColor)
                    Text("사용", fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f))
                }
            }
            Spacer(Modifier.width(20.dp))
            Column {
                Text(storage.readableUsed, fontSize = 26.sp, fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface)
                Text("/ ${storage.readableTotal}", fontSize = 14.sp,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f))
                Spacer(Modifier.height(10.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(8.dp).clip(RoundedCornerShape(4.dp)).background(primary))
                    Spacer(Modifier.width(6.dp))
                    Text("여유 ${storage.readableFree}", fontSize = 13.sp,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.75f))
                }
            }
        }
    }
}

@Composable
private fun MediaBreakdownCard(breakdown: List<MediaBreakdown>) {
    if (breakdown.isEmpty()) return
    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(16.dp)) {
            Text("📁 종류별 용량", fontWeight = FontWeight.Bold, fontSize = 15.sp)
            Spacer(Modifier.height(10.dp))
            breakdown.take(7).forEach { mb ->
                Row(
                    Modifier.fillMaxWidth().padding(vertical = 4.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(mb.type.emoji, fontSize = 18.sp)
                    Spacer(Modifier.width(10.dp))
                    Text(mb.type.label, fontSize = 14.sp, modifier = Modifier.weight(1f))
                    Text("${mb.count}개", fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f))
                    Spacer(Modifier.width(10.dp))
                    Text(mb.readableSize, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

@Composable
private fun FolderRow(folder: FolderNode, totalUsed: Long) {
    val frac = if (totalUsed > 0) (folder.sizeBytes.toFloat() / totalUsed).coerceIn(0f, 1f) else 0f
    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(horizontal = 14.dp, vertical = 10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(folder.name, fontSize = 14.sp, fontWeight = FontWeight.Medium,
                        maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text(folder.path.removePrefix("/storage/emulated/0"),
                        fontSize = 10.sp,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f),
                        maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
                Spacer(Modifier.width(8.dp))
                Text(folder.readableSize, fontWeight = FontWeight.Bold, fontSize = 14.sp,
                    color = MaterialTheme.colorScheme.primary)
            }
            Spacer(Modifier.height(6.dp))
            LinearProgressIndicator(
                progress = { frac },
                modifier = Modifier.fillMaxWidth().height(4.dp).clip(RoundedCornerShape(2.dp)),
                color = MaterialTheme.colorScheme.secondary,
            )
        }
    }
}

@Composable
private fun CategoryCard(vm: CleanViewModel, cat: CategoryResult) {
    var expanded by remember { mutableStateOf(false) }
    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column {
            Row(
                Modifier.fillMaxWidth().clickable { expanded = !expanded }
                    .padding(16.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(cat.category.emoji, fontSize = 22.sp)
                Spacer(Modifier.width(12.dp))
                Column(Modifier.weight(1f)) {
                    Text(cat.category.label, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                    Text("${cat.count}개 · ${cat.readableSize}", fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f))
                }
                Icon(
                    if (expanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                    contentDescription = null,
                )
            }
            if (expanded) {
                Divider(color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.1f))
                Row(
                    Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    TextButton(onClick = { vm.selectAll(cat, true) }) { Text("전체 선택") }
                    TextButton(onClick = { vm.selectAll(cat, false) }) { Text("선택 해제") }
                }
                cat.items.take(100).forEach { item ->
                    FileRow(vm, item)
                }
                if (cat.items.size > 100) {
                    Text(
                        "+ ${cat.items.size - 100}개 더 (상위 100개만 표시)",
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                        modifier = Modifier.padding(16.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun FileRow(vm: CleanViewModel, item: FileItem) {
    val selected = vm.isSelected(item)
    Row(
        Modifier.fillMaxWidth().clickable { vm.toggleSelect(item) }
            .padding(horizontal = 16.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Checkbox(checked = selected, onCheckedChange = { vm.toggleSelect(item) })
        Spacer(Modifier.width(4.dp))
        Column(Modifier.weight(1f)) {
            Text(item.name, fontSize = 13.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text(item.path.removePrefix("/storage/emulated/0"),
                fontSize = 9.sp,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f),
                maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
        Spacer(Modifier.width(8.dp))
        Text(item.readableSize, fontSize = 12.sp, fontWeight = FontWeight.Medium)
    }
}

@Composable
private fun DeleteBar(count: Int, bytes: Long, label: String, onDelete: () -> Unit) {
    var confirm by remember { mutableStateOf(false) }
    Surface(color = MaterialTheme.colorScheme.surfaceVariant, tonalElevation = 8.dp) {
        Row(
            Modifier.fillMaxWidth().padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text("${count}개 선택됨", fontWeight = FontWeight.Bold)
                Text("${formatSize(bytes)} 확보 가능", fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.primary)
            }
            Button(
                onClick = { confirm = true },
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.error
                ),
            ) {
                Icon(Icons.Default.Delete, contentDescription = null)
                Spacer(Modifier.width(6.dp))
                Text(label)
            }
        }
    }
    if (confirm) {
        AlertDialog(
            onDismissRequest = { confirm = false },
            title = { Text("정말 ${label}할까요?") },
            text = { Text("${count}개 (${formatSize(bytes)}) 대상입니다.") },
            confirmButton = {
                TextButton(onClick = { confirm = false; onDelete() }) {
                    Text(label, color = MaterialTheme.colorScheme.error)
                }
            },
            dismissButton = {
                TextButton(onClick = { confirm = false }) { Text("취소") }
            },
        )
    }
}

@Composable
private fun SectionTitle(text: String) {
    Text(
        text,
        fontWeight = FontWeight.Bold,
        fontSize = 17.sp,
        modifier = Modifier.padding(top = 8.dp, bottom = 2.dp),
    )
}
