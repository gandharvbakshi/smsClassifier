# Model Bake-Off Report

This report compares model candidates for reusable creative production roles.
Image candidates are judged as backgrounds under deterministic ad layout; video candidates are judged as secondary b-roll, not final UI-led install ads.

## Recommendation

- Image background winner: `google` / `imagen-4.0-fast-generate-001` (score 41.0).
- Video b-roll winner: `google` / `veo-3.1-fast-generate-preview` (score 33.0).

## Candidates

### image-fal-fal-ai-flux-schnell

- Kind: `image_background`
- Provider/model: `fal` / `fal-ai/flux/schnell`
- Status: `succeeded`
- Output: `D:\Projects\SMS datasets and project\ads\2026-06-17-model-bakeoff-fal\candidates\image-fal-fal-ai-flux-schnell\assets\otp_scam_benefit_headline_square_google_app_square.png`
- Selection score: `39.0`
- Checker verdict: `ship`; hard fails: none
- Key fix: While effective, exploring subtle variations in the abstract shapes or color palette could potentially enhance a thematic connection to digital security or communication, without adding clutter.
- Key strength: Provides excellent contrast for overlaid product UI, headlines, and logos.

### image-fal-fal-ai-ideogram-v3

- Kind: `image_background`
- Provider/model: `fal` / `fal-ai/ideogram/v3`
- Status: `succeeded`
- Output: `D:\Projects\SMS datasets and project\ads\2026-06-17-model-bakeoff-fal\candidates\image-fal-fal-ai-ideogram-v3\assets\otp_scam_benefit_headline_square_google_app_square.png`
- Selection score: `40.0`
- Checker verdict: `ship`; hard fails: none
- Key fix: Explore variations with slightly more dynamic lighting or subtle color shifts to add depth without increasing clutter.
- Key strength: Provides excellent contrast for overlaid deterministic text and product UI.

### image-fal-fal-ai-recraft-v4-pro-text-to-image

- Kind: `image_background`
- Provider/model: `fal` / `fal-ai/recraft/v4/pro/text-to-image`
- Status: `succeeded`
- Output: `D:\Projects\SMS datasets and project\ads\2026-06-17-model-bakeoff-fal\candidates\image-fal-fal-ai-recraft-v4-pro-text-to-image\assets\otp_scam_benefit_headline_square_google_app_square.png`
- Selection score: `30.0`
- Checker verdict: `revise`; hard fails: none
- Key fix: Explore background options that subtly hint at the SMS/communication or security/warning theme to better support the product category.
- Key strength: Provides excellent contrast for overlaid text and UI due to the dark background.

### image-google-imagen-4-0-fast-generate-001

- Kind: `image_background`
- Provider/model: `google` / `imagen-4.0-fast-generate-001`
- Status: `succeeded`
- Output: `D:\Projects\SMS datasets and project\ads\2026-06-17-model-bakeoff-fal\candidates\image-google-imagen-4-0-fast-generate-001\assets\otp_scam_benefit_headline_square_google_app_square.png`
- Selection score: `41.0`
- Checker verdict: `ship`; hard fails: none
- Key strength: Effectively provides secondary context for an SMS/messaging app with blurred chat bubbles.

### video-fal-bytedance-seedance-2-0-fast-text-to-video

- Kind: `video_broll`
- Provider/model: `fal` / `bytedance/seedance-2.0/fast/text-to-video`
- Status: `succeeded`
- Output: `D:\Projects\SMS datasets and project\ads\2026-06-17-model-bakeoff-fal\candidates\video-fal-bytedance-seedance-2-0-fast-text-to-video\assets\video\BROLL_FAL_BYTEDANCE_SEEDANCE_2_0_FAST_TEXT_TO_VIDEO.mp4`
- Selection score: `17.0`
- Checker verdict: `reject`; hard fails: Frames contain readable gibberish text ('SM') in the top-left corner, which is a hard fail.
- Key fix: Remove the 'SM' text artifact from the top-left corner to ensure a clean canvas for captions.
- Key strength: Conveys immediate human stakes through the actor's concerned expression.

### video-fal-fal-ai-kling-video-v2-master-text-to-video

- Kind: `video_broll`
- Provider/model: `fal` / `fal-ai/kling-video/v2/master/text-to-video`
- Status: `succeeded`
- Output: `D:\Projects\SMS datasets and project\ads\2026-06-17-model-bakeoff-fal\candidates\video-fal-fal-ai-kling-video-v2-master-text-to-video\assets\video\BROLL_FAL_FAL_AI_KLING_VIDEO_V2_MASTER_TEXT_TO_VIDEO.mp4`
- Selection score: `10.0`
- Checker verdict: `reject`; hard fails: Frames contain readable gibberish text on the phone screen, specifically in the first frame.
- Key fix: Replace the phone screen content with a blank screen, a generic non-text background, or clearly legible, non-gibberish placeholder text that supports the fraud warning narrative without being a fake system warning.
- Key strength: Conveys immediate human stakes through the actor's concerned expression.

### video-fal-fal-ai-minimax-hailuo-2-3-standard-text-to-video

- Kind: `video_broll`
- Provider/model: `fal` / `fal-ai/minimax/hailuo-2.3/standard/text-to-video`
- Status: `failed`
- Selection score: `-100.0`
- Error: `[{'type': 'literal_error', 'loc': ['body', 'duration'], 'msg': "Input should be '6' or '10'", 'input': '5', 'ctx': {'expected': "'6' or '10'"}}]`

### video-google-veo-3-1-fast-generate-preview

- Kind: `video_broll`
- Provider/model: `google` / `veo-3.1-fast-generate-preview`
- Status: `succeeded`
- Output: `D:\Projects\SMS datasets and project\ads\2026-06-17-model-bakeoff-fal\candidates\video-google-veo-3-1-fast-generate-preview\assets\video\BROLL_GOOGLE_VEO_3_1_FAST_GENERATE_PREVIEW.mp4`
- Selection score: `33.0`
- Automatic failures: `video_letterboxed_bars`
- Checker verdict: `ship`; hard fails: none
- Key strength: Strong emotional arc (happy to shocked to concerned) effectively creates immediate human stakes.
