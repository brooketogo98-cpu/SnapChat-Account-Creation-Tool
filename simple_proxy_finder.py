#!/usr/bin/env python3
"""Simple proxy finder that focuses on finding at least one working proxy"""

import requests
import time
import random

def get_proxies_from_source(url):
    """Get proxies from a source URL"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, timeout=10, headers=headers)
        if resp.status_code == 200:
            proxies = []
            for line in resp.text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    if ':' in line:
                        parts = line.split(':')
                        if len(parts) >= 2:
                            ip = parts[0].strip()
                            port = parts[1].strip()
                            # Clean port
                            port = ''.join(filter(str.isdigit, port))
                            if ip and port:
                                proxies.append(f"{ip}:{port}")
            return proxies
    except:
        pass
    return []

def test_proxy(proxy, test_url="http://httpbin.org/ip", timeout=5):
    """Test if a proxy works"""
    proxies = {
        'http': f'http://{proxy}',
        'https': f'http://{proxy}'
    }
    
    try:
        start = time.time()
        resp = requests.get(test_url, proxies=proxies, timeout=timeout, 
                           headers={'User-Agent': 'Mozilla/5.0'})
        elapsed = time.time() - start
        
        if resp.status_code == 200:
            # Check if we got a valid JSON response
            data = resp.json()
            if 'origin' in data:
                return True, elapsed, data['origin']
    except:
        pass
    
    return False, 0, None

def find_working_proxy(max_tries=50):
    """Try to find at least one working proxy"""
    sources = [
        'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt',
        'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt',
        'https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt',
    ]
    
    print("Looking for working proxies...")
    
    # Get proxies from all sources
    all_proxies = []
    for url in sources:
        proxies = get_proxies_from_source(url)
        if proxies:
            print(f"  {url}: {len(proxies)} proxies")
            all_proxies.extend(proxies)
    
    if not all_proxies:
        print("No proxies found from sources!")
        return None
    
    # Shuffle to try different ones
    random.shuffle(all_proxies)
    
    # Try proxies until we find one that works
    for i, proxy in enumerate(all_proxies[:max_tries]):
        print(f"  Testing {i+1}/{min(max_tries, len(all_proxies))}: {proxy}")
        works, speed, origin = test_proxy(proxy)
        
        if works:
            print(f"  ✓ Found working proxy: {proxy} ({speed:.2f}s)")
            print(f"  Origin IP: {origin}")
            return proxy
        
        time.sleep(0.5)  # Small delay between tests
    
    print("No working proxies found after testing")
    return None

def test_with_twitter(proxy):
    """Test if proxy can access Twitter"""
    print(f"\nTesting proxy {proxy} with Twitter...")
    
    proxies = {
        'http': f'http://{proxy}',
        'https': f'http://{proxy}'
    }
    
    try:
        # Try to access Twitter homepage
        resp = requests.get('https://twitter.com', proxies=proxies, timeout=10,
                           headers={'User-Agent': 'Mozilla/5.0'})
        
        if resp.status_code == 200:
            print("  ✓ Can access Twitter.com")
            return True
        else:
            print(f"  ✗ Twitter returned HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ Failed to access Twitter: {e}")
        return False

def main():
    print("=" * 60)
    print("Simple Proxy Finder for Twitter")
    print("=" * 60)
    
    # Find a working proxy
    proxy = find_working_proxy(max_tries=30)
    
    if proxy:
        print(f"\n✅ Found working proxy: {proxy}")
        
        # Test with Twitter
        if test_with_twitter(proxy):
            print("\n🎉 SUCCESS! This proxy can access Twitter.")
            print(f"\nYou can use this proxy: {proxy}")
            print("\nNext steps:")
            print("1. Use this proxy with browser automation")
            print("2. Create Twitter account with random credentials")
            print("3. Wait 24-48 hours before first action")
        else:
            print("\n⚠️  Proxy works but cannot access Twitter (may be blocked)")
    else:
        print("\n❌ No working proxies found.")
        print("\nThis is common with free proxies - they're often slow or blocked.")
        print("Consider:")
        print("1. Trying again later (proxy lists update frequently)")
        print("2. Using paid residential proxies for better success")
        print("3. Checking if your network allows proxy connections")

if __name__ == "__main__":
    main()