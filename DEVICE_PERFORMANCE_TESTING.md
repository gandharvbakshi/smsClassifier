# Device Performance Testing Guide

Since your app is now approved on Google Play, here are comprehensive methods to test performance across different devices.

## 1. Google Play Console Testing (Recommended)

### Pre-launch Reports (Automatic)
Google Play automatically tests your app on real devices before launch:

1. **Access Pre-launch Reports**
   - Go to [Google Play Console](https://play.google.com/console)
   - Navigate to **Release → Pre-launch report**
   - Reports show:
     - Crashes on different devices
     - Performance issues
     - Security vulnerabilities
     - Device compatibility issues

2. **View Device-Specific Results**
   - See test results for different Android versions
   - Check performance on various screen sizes
   - Review memory usage and ANR (App Not Responding) issues

### Internal Testing Track
Create a small test group with your own devices:

1. **Set Up Internal Testing**
   - Go to **Release → Testing → Internal testing**
   - Upload your app bundle (AAB)
   - Add testers via email
   - Testers install via Play Store link

2. **Monitor Performance**
   - Go to **Quality → Android vitals**
   - View crash reports by device
   - Check ANR rates by Android version
   - Monitor app startup time

## 2. Firebase Test Lab

Firebase Test Lab lets you test on real Google Cloud devices:

### Setup

1. **Create Firebase Project** (if not already done)
   ```bash
   # Install Firebase CLI (if needed)
   npm install -g firebase-tools
   firebase login
   ```

2. **Configure Firebase in Your App**
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Add Android app
   - Download `google-services.json`
   - Place in `android_sms_classifier/app/`

3. **Add Firebase to build.gradle.kts**
   ```kotlin
   // In project-level build.gradle.kts
   plugins {
       id("com.google.gms.google-services") version "4.4.0" apply false
   }

   // In app-level build.gradle.kts
   plugins {
       // ... existing plugins
       id("com.google.gms.google-services")
   }
   ```

### Run Tests

**Option A: Via Firebase Console (GUI)**
1. Go to [Firebase Test Lab](https://console.firebase.google.com/project/_/testlab)
2. Click **Run a test**
3. Upload your APK/AAB
4. Select devices (various Android versions, screen sizes)
5. Run performance tests

**Option B: Via Gradle (Command Line)**
```bash
# Build release APK
cd android_sms_classifier
./gradlew assembleRelease

# Run on Firebase Test Lab (requires gcloud CLI)
gcloud firebase test android run \
  --app app/build/outputs/apk/release/app-release.apk \
  --device model=Pixel7,version=33 \
  --device model=GalaxyS23,version=33 \
  --device model=Pixel6,version=31 \
  --timeout 20m
```

**Option C: Via Android Studio**
1. Build → Generate Signed Bundle/APK
2. After building, select **Run Tests on Firebase Test Lab**
3. Choose devices and run

## 3. Android Studio Profiler (Local Testing)

Test on connected devices/emulators with detailed profiling:

### Setup Profiling

1. **Connect Device/Start Emulator**
   - Connect via USB with USB debugging enabled
   - Or start Android Studio emulator

2. **Open Profiler**
   - Click **View → Tool Windows → Profiler**
   - Run your app (▶️)
   - Select your app process

### Monitor Performance Metrics

#### CPU Profiler
- **Track Inference Time**: Monitor ONNX model inference
- **View Thread Activity**: See if inference blocks UI thread
- **Record Method Calls**: Identify performance bottlenecks

#### Memory Profiler
- **Monitor Memory Usage**: Track heap size for model loading
- **Detect Memory Leaks**: Check for increasing memory
- **ONNX Runtime Memory**: Verify model memory usage is reasonable

#### Network Profiler
- **API Response Times**: Monitor server classification requests
- **Data Usage**: Track network bandwidth

#### Energy Profiler
- **Battery Impact**: See how much battery classification uses
- **Background Work**: Monitor WorkManager jobs

### Performance Testing Checklist

```kotlin
// Add to your code to log inference times
class OnDeviceClassifier {
    fun classify(message: String): ClassificationResult {
        val startTime = System.currentTimeMillis()
        // ... classification logic
        val endTime = System.currentTimeMillis()
        Log.d("Performance", "Inference time: ${endTime - startTime}ms")
        // ... return result
    }
}
```

## 4. Manual Testing on Real Devices

Test on your own devices or borrow devices:

### Device Matrix to Test

**Android Versions:**
- Android 8.0 (API 26) - minSdk
- Android 11 (API 30) - Common version
- Android 13 (API 33) - Recent version
- Android 14 (API 34) - Latest stable

**Device Categories:**
- **Budget** (e.g., Samsung Galaxy A series)
- **Mid-range** (e.g., Pixel 6a, OnePlus Nord)
- **Flagship** (e.g., Pixel 8, Samsung Galaxy S23)
- **Low-end** (older devices with limited RAM)

**Screen Sizes:**
- Small phones (< 5")
- Standard phones (5-6")
- Large phones (6-7")
- Tablets (if supporting)

### Testing Checklist Per Device

- [ ] App installs successfully
- [ ] SMS permission request works
- [ ] Classification inference time < 500ms (target)
- [ ] No ANRs during classification
- [ ] Memory usage stays under 200MB
- [ ] Background classification works (WorkManager)
- [ ] UI remains responsive during classification
- [ ] App handles low memory gracefully
- [ ] Battery usage is reasonable

## 5. Performance Benchmarks

Create a benchmark test to measure performance consistently:

### Create Performance Test

```kotlin
// android_sms_classifier/app/src/androidTest/java/com/smsclassifier/app/PerformanceTest.kt
package com.smsclassifier.app

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.smsclassifier.app.classification.OnDeviceClassifier
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.junit.Assert.assertTrue

@RunWith(AndroidJUnit4::class)
class PerformanceTest {
    
    private lateinit var classifier: OnDeviceClassifier
    
    @Before
    fun setup() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        classifier = OnDeviceClassifier(context)
    }
    
    @Test
    fun testInferencePerformance() {
        val testMessages = listOf(
            "Your OTP is 123456",
            "Click here to claim your prize!",
            "Your Amazon order #12345 is delivered"
        )
        
        val times = mutableListOf<Long>()
        
        testMessages.forEach { message ->
            val startTime = System.currentTimeMillis()
            classifier.classify(message)
            val endTime = System.currentTimeMillis()
            times.add(endTime - startTime)
        }
        
        val averageTime = times.average()
        val maxTime = times.maxOrNull() ?: 0L
        
        // Assertions
        assertTrue("Average inference should be < 500ms", averageTime < 500)
        assertTrue("Max inference should be < 1000ms", maxTime < 1000)
        
        println("Average inference time: ${averageTime}ms")
        println("Max inference time: ${maxTime}ms")
    }
    
    @Test
    fun testBatchClassificationPerformance() {
        val messages = List(100) { "Test message $it with OTP 123456" }
        
        val startTime = System.currentTimeMillis()
        messages.forEach { classifier.classify(it) }
        val endTime = System.currentTimeMillis()
        
        val totalTime = endTime - startTime
        val averageTime = totalTime / messages.size.toDouble()
        
        println("Batch of 100 messages: ${totalTime}ms total, ${averageTime}ms average")
        assertTrue("Average batch time should be < 1000ms", averageTime < 1000)
    }
}
```

### Run Performance Tests

```bash
cd android_sms_classifier

# Run on connected device
./gradlew connectedAndroidTest

# Run on specific device
adb devices  # List devices
./gradlew connectedAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=com.smsclassifier.app.PerformanceTest
```

## 6. Production Monitoring

Once your app is live, monitor performance in production:

### Google Play Console - Android Vitals

1. **Access Android Vitals**
   - Go to **Quality → Android vitals**
   - View real-world performance metrics:
     - Crash rate by device
     - ANR rate by Android version
     - App startup time
     - Frame rendering performance

2. **Filter by Device**
   - Filter crashes by device model
   - Filter ANRs by Android version
   - Identify device-specific issues

### Firebase Performance Monitoring (Optional)

Add Firebase Performance Monitoring for detailed metrics:

1. **Add Dependency**
   ```kotlin
   // In app/build.gradle.kts
   implementation("com.google.firebase:firebase-perf-ktx:1.4.2")
   ```

2. **Add Custom Traces**
   ```kotlin
   import com.google.firebase.perf.metrics.Trace
   
   class OnDeviceClassifier {
       fun classify(message: String): ClassificationResult {
           val trace = FirebasePerformance.getInstance()
               .newTrace("classification_inference")
           trace.start()
           
           try {
               // ... classification logic
           } finally {
               trace.stop()
           }
       }
   }
   ```

3. **View Metrics**
   - Go to Firebase Console → Performance
   - See average inference times
   - View device-specific performance

## 7. Device Farm Services

### AWS Device Farm
- Test on 2,500+ real devices
- Automated testing
- Performance profiling

### BrowserStack App Live
- Test on real devices remotely
- Manual and automated testing
- Performance monitoring

### Sauce Labs
- Mobile device testing
- Real device cloud
- Performance benchmarking

## 8. Quick Testing Checklist

### Before Testing
- [ ] Build release APK/AAB
- [ ] Sign with release keystore
- [ ] Enable ProGuard mapping upload (for crash reports)

### During Testing
- [ ] Test on minimum SDK (API 26)
- [ ] Test on target SDK (API 35)
- [ ] Test on mid-range Android version (API 30-33)
- [ ] Test on devices with < 4GB RAM
- [ ] Test classification with 100+ messages
- [ ] Monitor memory during long sessions
- [ ] Test background classification

### After Testing
- [ ] Review crash reports in Play Console
- [ ] Check ANR reports
- [ ] Monitor user reviews for performance issues
- [ ] Set up alerts for performance degradation

## 9. Performance Goals

Target metrics for your SMS Classifier app:

| Metric | Target | Acceptable |
|--------|--------|------------|
| Inference Time (Single) | < 200ms | < 500ms |
| Inference Time (Batch 100) | < 10s | < 30s |
| Memory Usage | < 150MB | < 250MB |
| ANR Rate | < 0.1% | < 0.5% |
| Crash Rate | < 0.1% | < 0.5% |
| Battery Impact | Minimal | Low |

## 10. Troubleshooting Performance Issues

### Slow Inference
- Check ONNX model size (should be < 5MB total)
- Verify model is optimized
- Consider using NNAPI acceleration
- Profile with Android Studio Profiler

### High Memory Usage
- Check for memory leaks in classification code
- Verify models are loaded once and cached
- Monitor WorkManager background jobs

### ANRs (App Not Responding)
- Ensure classification runs off UI thread
- Use coroutines/threading for inference
- Check database operations aren't blocking

## Next Steps

1. **Start with Pre-launch Reports** - Already available in Play Console
2. **Set up Internal Testing** - Test with real users
3. **Configure Android Studio Profiler** - Detailed local testing
4. **Consider Firebase Test Lab** - Automated device testing
5. **Monitor Android Vitals** - Track production performance

---

**Pro Tip**: Start with Google Play Console's Pre-launch Reports and Android Vitals - they're free and automatically test on real devices!
