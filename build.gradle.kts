// Top-level build file
plugins {
    id("com.android.application") version "8.2.0" apply false
    id("org.jetbrains.kotlin.android") version "1.9.24" apply false
    id("org.jetbrains.kotlin.plugin.serialization") version "1.9.24" apply false
    id("com.google.devtools.ksp") version "1.9.24-1.0.20" apply false
    // Gradle Play Publisher — uploads signed AABs to Google Play.
    // Apply only in :app. Run `./gradlew publishReleaseBundle` to release.
    id("com.github.triplet.play") version "3.10.1" apply false
}

