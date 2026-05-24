package com.cleanspace.app.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val DarkColors = darkColorScheme(
    primary = Color(0xFF5ED4A3),
    onPrimary = Color(0xFF003828),
    secondary = Color(0xFF4D7CFF),
    background = Color(0xFF101219),
    surface = Color(0xFF1A1D27),
    surfaceVariant = Color(0xFF252938),
    onBackground = Color(0xFFE8E9F3),
    onSurface = Color(0xFFE8E9F3),
    error = Color(0xFFFF6B6B),
)

private val LightColors = lightColorScheme(
    primary = Color(0xFF1FA97B),
    secondary = Color(0xFF4D7CFF),
    background = Color(0xFFF6F7FB),
    surface = Color(0xFFFFFFFF),
    error = Color(0xFFD32F2F),
)

@Composable
fun CleanSpaceTheme(content: @Composable () -> Unit) {
    val colors = if (isSystemInDarkTheme()) DarkColors else LightColors
    MaterialTheme(colorScheme = colors, content = content)
}
