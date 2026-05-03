"""End-to-end test of the new Cloud Run revision: send 3 SMS through /api/classify
and check whether Groq is now succeeding (no more 401 errors)."""
import json
import urllib.request

URL = "https://sms-ensemble-hhpimusmbq-el.a.run.app/api/classify"
SAMPLES = [
    # Real OTP (jury said app missed these in old run; should now classify correctly)
    {"sender": "AD-ICICIO-T",
     "text": "914877 is One-Time Password for INR 374.00 transaction towards AMAZON using "
             "ICICI Bank Credit Card XX7007. OTPs are SECRET. DO NOT disclose"},
    # OTP that may force the Groq intent path (heuristic might say no, ML may say yes)
    {"sender": "TX-AMAZON-S",
     "text": "Your Amazon login OTP is 539218. Do not share with anyone. Valid for 10 mins."},
    # Transaction notification (should be is_otp=False)
    {"sender": "JX-ICICIT-S",
     "text": "INR 388.00 spent using ICICI Bank Card XX7007 on 02-May-26 on Swiggy Limited. "
             "Avl Limit: INR 4,22,704.15."},
]

for s in SAMPLES:
    req = urllib.request.Request(
        URL,
        data=json.dumps(s).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.loads(r.read())
    print(f"sender={s['sender']!r}")
    print(f"  body: {s['text'][:80]}...")
    print(f"  isOtp={body['isOtp']}  intent={body['otpIntent']}  "
          f"phish={body['isPhishing']} ({body['phishScore']:.2f})")
    groq_lines = [x for x in body["reasons"] if "roq" in x.lower()]
    error_lines = [x for x in body["reasons"] if "fail" in x.lower() or "401" in x or "error" in x.lower()]
    if groq_lines:
        print(f"  Groq reasons: {groq_lines}")
    if error_lines:
        print(f"  ERROR reasons: {error_lines}")
    print()
