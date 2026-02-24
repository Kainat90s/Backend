import time
import requests
import statistics

BASE_URL = "http://127.0.0.1:8000/api"

def test_endpoint(name, path, iterations=10):
    print(f"\nTesting {name} ({path}):")
    latencies = []
    for _ in range(iterations):
        start = time.perf_counter()
        try:
            response = requests.get(f"{BASE_URL}{path}")
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)
        except Exception as e:
            print(f"Error: {e}")
            return
    
    avg = sum(latencies) / len(latencies)
    print(f"  Iterations: {iterations}")
    print(f"  Average Latency: {avg:.2f}ms")
    print(f"  Min Latency: {min(latencies):.2f}ms")
    print(f"  Max Latency: {max(latencies):.2f}ms")
    if iterations > 1:
        print(f"  Std Dev: {statistics.stdev(latencies):.2f}ms")

if __name__ == "__main__":
    print("Performance Verification Script")
    # Public endpoint - should be fast (cached)
    test_endpoint("Public Slots", "/availability/slots/", iterations=20)
    
    # Dashboard endpoint (requires auth manually or mock session if needed)
    # Since I'm in a verify context, I'll focus on what I can access or describe the results
    print("\nNote: Dashboard latency should be checked manually with an authenticated session.")
