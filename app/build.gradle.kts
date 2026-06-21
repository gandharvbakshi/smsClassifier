plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.serialization")
    id("com.google.devtools.ksp") version "1.9.24-1.0.20"
    id("com.github.triplet.play")
    id("com.google.gms.google-services")
    id("com.google.firebase.crashlytics")
}

// Load keystore properties for signing
import java.io.File
import java.io.FileInputStream
import java.nio.charset.StandardCharsets
import java.util.Properties

val keystorePropertiesFile = rootProject.file("keystore.properties")
val keystoreProperties = Properties()
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(FileInputStream(keystorePropertiesFile))
}

android {
    namespace = "com.smsclassifier.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.smsclassifier.app"
        minSdk = 26
        targetSdk = 35
        versionCode = 38
        versionName = "1.2.13"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables {
            useSupportLibrary = true
        }

        buildConfigField(
            "String",
            "SERVER_API_BASE_URL",
            "\"https://sms-ensemble-hhpimusmbq-el.a.run.app/api\""
        )
    }
    
    signingConfigs {
        // Use keystore.properties if it exists (for Google Play)
        if (keystorePropertiesFile.exists()) {
            create("release") {
                keyAlias = keystoreProperties["keyAlias"] as String
                keyPassword = keystoreProperties["keyPassword"] as String
                // Resolve storeFile relative to root project directory
                val storeFileValue = keystoreProperties["storeFile"] as String?
                storeFile = storeFileValue?.let { 
                    rootProject.file(it) 
                }
                storePassword = keystoreProperties["storePassword"] as String
            }
        } else {
            // Fallback: use debug keystore for local testing only
            // WARNING: This will NOT work for Google Play Store!
            create("release") {
                storeFile = file("${System.getProperty("user.home")}/.android/debug.keystore")
                storePassword = "android"
                keyAlias = "androiddebugkey"
                keyPassword = "android"
            }
        }
    }
    
    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            signingConfig = signingConfigs.getByName("release")
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            // Generate native debug symbols for crash reporting
            ndk {
                debugSymbolLevel = "FULL"
            }
        }
        debug {
            isDebuggable = true
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.14"
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
        jniLibs {
            useLegacyPackaging = true
        }
    }
    
    ndkVersion = "26.1.10909125"
}

ksp {
    arg("room.schemaLocation", "$projectDir/schemas")
}

dependencies {
    // Firebase (BoM aligns versions)
    implementation(platform("com.google.firebase:firebase-bom:33.7.0"))
    implementation("com.google.firebase:firebase-analytics-ktx")
    implementation("com.google.firebase:firebase-crashlytics-ktx")
    implementation("com.google.firebase:firebase-installations-ktx")
    implementation("com.google.firebase:firebase-config-ktx")
    implementation("com.google.firebase:firebase-auth-ktx")
    implementation("androidx.datastore:datastore-preferences:1.1.1")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.6.2")

    // Core Android
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.fragment:fragment:1.8.9")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.6.2")
    implementation("androidx.activity:activity-compose:1.8.1")

    // Compose
    implementation(platform("androidx.compose:compose-bom:2024.06.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")

    // Navigation
    implementation("androidx.navigation:navigation-compose:2.7.5")

    // Room Database
    val roomVersion = "2.6.1"
    implementation("androidx.room:room-runtime:$roomVersion")
    implementation("androidx.room:room-ktx:$roomVersion")
    implementation("androidx.room:room-paging:$roomVersion")
    ksp("androidx.room:room-compiler:$roomVersion")

    // WorkManager
    implementation("androidx.work:work-runtime-ktx:2.9.0")

    // ONNX Runtime
    implementation("com.microsoft.onnxruntime:onnxruntime-android:1.17.0")

    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-play-services:1.7.3")

    // JSON
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.0")

    // HTTP Client (for server classifier)
    implementation("com.squareup.okhttp3:okhttp:4.12.0")

    // ViewModel
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.6.2")

    // Paging
    implementation("androidx.paging:paging-runtime-ktx:3.2.1")
    implementation("androidx.paging:paging-compose:3.2.1")

    implementation("io.coil-kt:coil-compose:2.5.0")

    // Play Billing & in-app review (monetization plan)
    implementation("com.android.billingclient:billing-ktx:7.1.1")
    implementation("com.google.android.play:review-ktx:2.0.1")

    // Testing
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")
    androidTestImplementation(platform("androidx.compose:compose-bom:2024.06.00"))
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-tooling")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}

// ---------------------------------------------------------------------------
// Gradle Play Publisher
//
// Configures `./gradlew publishReleaseBundle` to upload the signed release AAB
// to Google Play. See RELEASE_AUTOPUBLISH_SETUP.md for one-time setup.
//
// Defaults:
//   - track: "beta" (maps to **Open testing** in Play Console; use
//     `--track=internal` for internal-only testers, or `production` when ready)
//   - format: AAB (.aab), not APK
//   - status: COMPLETED (immediate release on the chosen track)
//   - resolutionStrategy: IGNORE (does not call Play during `assembleRelease`
//     or `bundleRelease`). Bump `versionCode` in this file before each upload
//     if Play already has that code. For auto versionCode from the store, use
//     AUTO after enabling Android Publisher API — see RELEASE_AUTOPUBLISH_SETUP.md
//
// Override the track per-build: `./gradlew publishReleaseBundle --track=beta`
// ---------------------------------------------------------------------------
play {
    // Prefer app/play-publisher.json; otherwise use any JSON key in app/
    // whose body looks like a GCP service-account (Cloud Console downloads
    // often name it `<project>-<hex>.json` instead).
    val appDir = layout.projectDirectory.asFile
    val credsFile =
        sequenceOf(File(appDir, "play-publisher.json"))
            .plus(
                appDir.listFiles()?.filter { f ->
                    f.isFile && f.extension.equals("json", ignoreCase = true)
                }.orEmpty().sorted(),
            )
            .firstOrNull { f ->
                if (!f.exists()) return@firstOrNull false
                runCatching {
                    val txt = f.readText(StandardCharsets.UTF_8)
                    txt.contains("\"type\"") &&
                        txt.contains("service_account") &&
                        txt.contains("client_email")
                }.getOrDefault(false)
            }
    if (credsFile != null) {
        serviceAccountCredentials.set(credsFile)
    }
    track.set("beta")
    defaultToAppBundles.set(true)
    releaseStatus.set(com.github.triplet.gradle.androidpublisher.ReleaseStatus.COMPLETED)
    resolutionStrategy.set(com.github.triplet.gradle.androidpublisher.ResolutionStrategy.IGNORE)
}

