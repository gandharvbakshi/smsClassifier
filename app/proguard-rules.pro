# Add project specific ProGuard rules here.

# Keep app classes
-keep class com.smsclassifier.app.** { *; }

# Keep ONNX Runtime
-keep class ai.onnxruntime.** { *; }

# Keep Kotlin serialization
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.AnnotationsKt
-keepclassmembers class kotlinx.serialization.json.** {
    *** Companion;
}
-keepclasseswithmembers class kotlinx.serialization.json.** {
    kotlinx.serialization.KSerializer serializer(...);
}

# Keep Room entities
-keep class * extends androidx.room.RoomDatabase
-keep @androidx.room.Entity class *
-keep class * extends androidx.room.RoomDatabase$Callback

# Keep WorkManager
-keep class androidx.work.** { *; }
-dontwarn androidx.work.**

# Remove debug logging in release (only Log.d, Log.v, Log.i)
-assumenosideeffects class android.util.Log {
    public static *** d(...);
    public static *** v(...);
    public static *** i(...);
}

# Keep BuildConfig
-keep class com.smsclassifier.app.BuildConfig { *; }

# Keep OkHttp
-keep class okhttp3.** { *; }
-keep interface okhttp3.** { *; }
-dontwarn okhttp3.**

