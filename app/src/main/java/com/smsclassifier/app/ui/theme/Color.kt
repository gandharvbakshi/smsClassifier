package com.smsclassifier.app.ui.theme

import androidx.compose.ui.graphics.Color

// === Brand palette (Microsoft SMS Organizer-inspired blue) ===
val BrandBlue = Color(0xFF0067C0)
val BrandBlueLight = Color(0xFF4A90E2)
val BrandBlueDark = Color(0xFF003F7F)

// Light scheme
val LightBackground = Color(0xFFF7F9FC)
val LightSurface = Color(0xFFFFFFFF)
val LightSurfaceVariant = Color(0xFFEEF1F6)
val LightOnBackground = Color(0xFF1B1C1E)
val LightOnSurfaceVariant = Color(0xFF5A5F66)

// Dark scheme
val DarkBackground = Color(0xFF101418)
val DarkSurface = Color(0xFF181C20)
val DarkSurfaceVariant = Color(0xFF22272D)
val DarkOnBackground = Color(0xFFE6E8EB)
val DarkOnSurfaceVariant = Color(0xFFB0B5BC)

// === Semantic / classification colors ===
val SafeGreen = Color(0xFF2E7D32)
val SafeGreenSoft = Color(0xFFE6F4EA)
val SuspiciousAmber = Color(0xFFE08A00)
val SuspiciousAmberSoft = Color(0xFFFFF4E0)
val PhishingRed = Color(0xFFD32F2F)
val PhishingRedSoft = Color(0xFFFCE7E7)
val OTPBlue = Color(0xFF0067C0)
val OTPBlueSoft = Color(0xFFE3F0FB)

val DoNotShareOrange = Color(0xFFE25822)
val CourierBlue = Color(0xFF3F51B5)
val InfoGray = Color(0xFF5F6B7A)

// Avatar palette — deterministic colors per contact
val AvatarPalette = listOf(
    Color(0xFF1976D2),
    Color(0xFF388E3C),
    Color(0xFFE65100),
    Color(0xFF6A1B9A),
    Color(0xFFC62828),
    Color(0xFF00838F),
    Color(0xFFAD1457),
    Color(0xFF455A64)
)

fun avatarColor(seed: String): Color {
    if (seed.isEmpty()) return AvatarPalette[0]
    val idx = (seed.hashCode().rem(AvatarPalette.size) + AvatarPalette.size) % AvatarPalette.size
    return AvatarPalette[idx]
}
