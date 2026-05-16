"""
Test script to verify SMS Provider accessibility for OTP auto-fill apps.
Uses ADB to query the SMS provider and verify it returns messages correctly.
"""

import subprocess
import json
import sys
from pathlib import Path

def run_adb_command(command: str) -> tuple[str, int]:
    """Run ADB shell command and return output and return code."""
    try:
        result = subprocess.run(
            ["adb", "shell", command],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout, result.returncode
    except subprocess.TimeoutExpired:
        return "", -1
    except FileNotFoundError:
        return "Error: ADB not found. Please ensure Android SDK platform-tools are in PATH.", -1
    except Exception as e:
        return f"Error: {str(e)}", -1

def test_sms_provider_uris():
    """Test various SMS provider URIs to see which ones work."""
    print("Testing SMS Provider Access")
    print("=" * 80)
    
    # Test URIs that OTP apps typically use
    test_uris = [
        "content://sms/inbox",
        "content://sms",
        "content://sms/inbox?limit=5",
        "content://sms/inbox?_sort=date DESC&_limit=5",
    ]
    
    # Standard SMS columns that OTP apps typically query
    test_columns = [
        "_id,address,body,date,type,read",
        "_id,address,body,date",
        "body",  # Minimal query - just the message body
    ]
    
    results = []
    
    for uri in test_uris:
        print(f"\nTesting URI: {uri}")
        print("-" * 80)
        
        for columns in test_columns:
            command = f'content query --uri "{uri}" --projection {columns}'
            output, return_code = run_adb_command(command)
            
            result = {
                "uri": uri,
                "columns": columns,
                "return_code": return_code,
                "output_length": len(output),
                "success": return_code == 0
            }
            
            if return_code == 0:
                lines = output.strip().split('\n')
                result["row_count"] = len([l for l in lines if l.startswith("Row:")])
                print(f"  Columns: {columns}")
                print(f"  ✓ Success - {result['row_count']} rows returned")
                if result["row_count"] > 0:
                    # Show first few rows
                    for line in lines[:5]:
                        if line.startswith("Row:"):
                            print(f"    {line[:100]}")
            else:
                print(f"  Columns: {columns}")
                print(f"  ✗ Failed - Return code: {return_code}")
                if output:
                    print(f"    Error: {output[:200]}")
            
            results.append(result)
    
    # Test with package name authority (our custom authority)
    package_name = "com.smsclassifier.app"
    custom_uris = [
        f"content://{package_name}.smsprovider/sms/inbox",
        f"content://{package_name}.smsprovider/sms",
    ]
    
    print(f"\n\nTesting Custom Authority URIs")
    print("=" * 80)
    
    for uri in custom_uris:
        print(f"\nTesting URI: {uri}")
        print("-" * 80)
        command = f'content query --uri "{uri}" --projection _id,address,body,date'
        output, return_code = run_adb_command(command)
        
        if return_code == 0:
            lines = output.strip().split('\n')
            row_count = len([l for l in lines if l.startswith("Row:")])
            print(f"  ✓ Success - {row_count} rows returned")
        else:
            print(f"  ✗ Failed - Return code: {return_code}")
            if output:
                print(f"    Error: {output[:200]}")
    
    # Generate summary report
    print("\n\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    print(f"Successful queries: {len(successful)}/{len(results)}")
    print(f"Failed queries: {len(failed)}/{len(results)}")
    
    if successful:
        print("\nSuccessful URIs:")
        for r in successful:
            print(f"  - {r['uri']} (columns: {r['columns']}) - {r.get('row_count', 0)} rows")
    
    if failed:
        print("\nFailed URIs:")
        for r in failed:
            print(f"  - {r['uri']} (columns: {r['columns']})")
    
    # Save results
    output_dir = Path(__file__).parent.parent / "sms_provider_test_results"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = output_dir / "provider_access_test_report.json"
    with open(report_file, "w") as f:
        json.dump({
            "summary": {
                "total_tests": len(results),
                "successful": len(successful),
                "failed": len(failed)
            },
            "results": results
        }, f, indent=2)
    
    print(f"\nDetailed report saved to: {report_file}")
    
    return len(successful) > 0

def main():
    print("SMS Provider Access Test")
    print("Make sure:")
    print("1. Device is connected via USB")
    print("2. USB debugging is enabled")
    print("3. App is set as default SMS handler")
    print("4. App has at least a few SMS messages")
    print("\n")
    
    input("Press Enter to continue...")
    
    # Check if ADB is available
    _, return_code = run_adb_command("echo test")
    if return_code != 0:
        print("ERROR: ADB not available. Please check:")
        print("1. Android SDK platform-tools installed")
        print("2. ADB is in your PATH")
        print("3. Device is connected")
        return
    
    # Check if device is connected
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    devices = [line for line in result.stdout.split('\n') if '\tdevice' in line]
    if not devices:
        print("ERROR: No devices connected")
        print("Please connect your device and enable USB debugging")
        return
    
    print(f"Found {len(devices)} device(s)")
    
    # Run tests
    success = test_sms_provider_uris()
    
    if success:
        print("\n✓ Some queries succeeded - Provider is accessible")
    else:
        print("\n✗ All queries failed - Provider may not be accessible")
        print("\nTroubleshooting:")
        print("1. Verify app is set as default SMS handler")
        print("2. Check app logs for SmsProvider query logs")
        print("3. Verify provider authority in AndroidManifest.xml")
        print("4. Restart device after setting as default SMS handler")

if __name__ == "__main__":
    main()

