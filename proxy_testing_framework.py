#!/usr/bin/env python3
"""
Comprehensive Proxy Testing Framework
Multi-source proxy validation with detailed metrics and reporting
"""

import asyncio
import aiohttp
import time
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
from datetime import datetime, timedelta

class ProxyType(Enum):
    UNKNOWN = "unknown"
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"
    RESIDENTIAL = "residential"
    DATACENTER = "datacenter"
    MOBILE = "mobile"

class AnonymityLevel(Enum):
    TRANSPARENT = "transparent"  # Shows client IP
    ANONYMOUS = "anonymous"      # Hides client IP but reveals proxy
    ELITE = "elite"              # Hides both client IP and proxy usage

@dataclass
class ProxyTestResult:
    """Results from testing a single proxy"""
    proxy: str
    is_working: bool = False
    response_time_ms: float = 0.0
    anonymity: AnonymityLevel = AnonymityLevel.TRANSPARENT
    proxy_type: ProxyType = ProxyType.UNKNOWN
    country: str = "Unknown"
    city: str = "Unknown"
    organization: str = "Unknown"
    tested_at: datetime = None
    error_message: str = ""
    
    def __post_init__(self):
        if self.tested_at is None:
            self.tested_at = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['anonymity'] = self.anonymity.value
        data['proxy_type'] = self.proxy_type.value
        data['tested_at'] = self.tested_at.isoformat()
        return data

@dataclass
class TestMetrics:
    """Aggregated metrics for a test run"""
    total_tested: int = 0
    working_count: int = 0
    average_response_time: float = 0.0
    median_response_time: float = 0.0
    success_rate: float = 0.0
    anonymity_distribution: Dict[str, int] = None
    type_distribution: Dict[str, int] = None
    top_countries: List[Tuple[str, int]] = None
    
    def __post_init__(self):
        if self.anonymity_distribution is None:
            self.anonymity_distribution = {}
        if self.type_distribution is None:
            self.type_distribution = {}
        if self.top_countries is None:
            self.top_countries = []
    
    def calculate(self, results: List[ProxyTestResult]):
        """Calculate metrics from test results"""
        self.total_tested = len(results)
        self.working_count = sum(1 for r in results if r.is_working)
        
        if self.working_count > 0:
            working_times = [r.response_time_ms for r in results if r.is_working]
            self.average_response_time = statistics.mean(working_times)
            self.median_response_time = statistics.median(working_times)
        
        self.success_rate = (self.working_count / self.total_tested * 100) if self.total_tested > 0 else 0
        
        # Anonymity distribution
        self.anonymity_distribution = {}
        for result in results:
            if result.is_working:
                anonymity = result.anonymity.value
                self.anonymity_distribution[anonymity] = self.anonymity_distribution.get(anonymity, 0) + 1
        
        # Type distribution
        self.type_distribution = {}
        for result in results:
            if result.is_working:
                proxy_type = result.proxy_type.value
                self.type_distribution[proxy_type] = self.type_distribution.get(proxy_type, 0) + 1
        
        # Top countries
        country_counts = {}
        for result in results:
            if result.is_working and result.country != "Unknown":
                country_counts[result.country] = country_counts.get(result.country, 0) + 1
        
        self.top_countries = sorted(
            country_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]

class ProxyTester:
    """Main proxy testing class with async validation"""
    
    def __init__(self, max_concurrent_tests: int = 50, timeout: float = 10.0):
        self.max_concurrent_tests = max_concurrent_tests
        self.timeout = timeout
        self.results: List[ProxyTestResult] = []
        
    async def test_single_proxy(self, proxy: str, session: aiohttp.ClientSession) -> ProxyTestResult:
        """Test a single proxy with multiple validation steps"""
        result = ProxyTestResult(proxy=proxy)
        start_time = time.time()
        
        try:
            # Step 1: Basic connectivity test
            proxy_url = f"http://{proxy}"
            connector = aiohttp.TCPConnector(ssl=False)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as test_session:
                
                # Test with httpbin.org
                test_url = "http://httpbin.org/ip"
                async with test_session.get(
                    test_url,
                    proxy=proxy_url,
                    headers={'User-Agent': 'ProxyTester/1.0'}
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        result.is_working = True
                        result.response_time_ms = (time.time() - start_time) * 1000
                        
                        # Determine anonymity
                        if 'origin' in data:
                            origin_ip = data['origin']
                            # Check if origin matches proxy IP (simplified)
                            proxy_ip = proxy.split(':')[0]
                            if proxy_ip in origin_ip:
                                result.anonymity = AnonymityLevel.ANONYMOUS
                            else:
                                result.anonymity = AnonymityLevel.ELITE
                        
                        # Determine proxy type (simplified heuristic)
                        if proxy_ip.startswith(('104.', '172.', '192.')):
                            result.proxy_type = ProxyType.DATACENTER
                        elif proxy_ip.startswith(('5.', '31.', '185.')):
                            result.proxy_type = ProxyType.RESIDENTIAL
                        else:
                            result.proxy_type = ProxyType.HTTP
                        
                    else:
                        result.error_message = f"HTTP {response.status}"
                
        except asyncio.TimeoutError:
            result.error_message = "Timeout"
        except Exception as e:
            result.error_message = str(e)
        
        return result
    
    async def test_batch(self, proxies: List[str]) -> List[ProxyTestResult]:
        """Test a batch of proxies concurrently"""
        print(f"Testing {len(proxies)} proxies (max concurrent: {self.max_concurrent_tests})")
        
        semaphore = asyncio.Semaphore(self.max_concurrent_tests)
        
        async def test_with_semaphore(proxy: str) -> ProxyTestResult:
            async with semaphore:
                async with aiohttp.ClientSession() as session:
                    return await self.test_single_proxy(proxy, session)
        
        tasks = [test_with_semaphore(proxy) for proxy in proxies]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Error testing proxy {proxies[i]}: {result}")
                continue
            valid_results.append(result)
            
            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"  Tested {i + 1}/{len(proxies)} proxies")
        
        self.results.extend(valid_results)
        return valid_results
    
    def get_metrics(self) -> TestMetrics:
        """Calculate and return test metrics"""
        metrics = TestMetrics()
        metrics.calculate(self.results)
        return metrics
    
    def save_results(self, filename: str = "proxy_test_results.json"):
        """Save results to JSON file"""
        data = {
            'tested_at': datetime.now().isoformat(),
            'results': [r.to_dict() for r in self.results],
            'metrics': asdict(self.get_metrics())
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"Results saved to {filename}")

class ProxySourceFetcher:
    """Fetch proxies from multiple GitHub sources"""
    
    GITHUB_SOURCES = [
        # High-frequency sources (updated every few minutes)
        "https://raw.githubusercontent.com/themiralay/Proxy-List-World/master/proxy-list.txt",
        "https://raw.githubusercontent.com/Mohammedcha/ProxRipper/main/proxies.txt",
        "https://raw.githubusercontent.com/saschazesiger/Free-Proxies/master/proxies.txt",
        
        # Daily updated sources
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list.txt",
        "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
        "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxies.txt",
        "https://raw.githubusercontent.com/roosterkid/openproxylist/main/http.txt",
    ]
    
    @staticmethod
    def parse_proxy_line(line: str) -> Optional[str]:
        """Parse a line from proxy list and return IP:PORT"""
        line = line.strip()
        if not line or line.startswith('#'):
            return None
        
        # Handle various formats
        if ':' in line:
            parts = line.split(':')
            if len(parts) >= 2:
                ip = parts[0].strip()
                port = parts[1].strip()
                
                # Clean port - keep only digits
                port = ''.join(filter(str.isdigit, port))
                
                if ip and port:
                    return f"{ip}:{port}"
        
        return None
    
    async def fetch_from_source(self, url: str, session: aiohttp.ClientSession) -> List[str]:
        """Fetch proxies from a single source"""
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    text = await response.text()
                    proxies = []
                    for line in text.split('\n'):
                        proxy = self.parse_proxy_line(line)
                        if proxy:
                            proxies.append(proxy)
                    return proxies
        except Exception as e:
            print(f"Error fetching from {url}: {e}")
        
        return []
    
    async def fetch_all_sources(self) -> List[str]:
        """Fetch proxies from all sources and deduplicate"""
        print(f"Fetching proxies from {len(self.GITHUB_SOURCES)} sources...")
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for url in self.GITHUB_SOURCES:
                task = self.fetch_from_source(url, session)
                tasks.append(task)
                
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            all_proxies = []
            source_counts = {}
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"  Source {i + 1}: Error - {result}")
                    continue
                
                proxies = result
                source_counts[self.GITHUB_SOURCES[i]] = len(proxies)
                all_proxies.extend(proxies)
                
                if proxies:
                    print(f"  Source {i + 1}: {len(proxies)} proxies")
                else:
                    print(f"  Source {i + 1}: No proxies found")
            
            # Deduplicate
            unique_proxies = list(set(all_proxies))
            print(f"\nTotal unique proxies: {len(unique_proxies)}")
            
            # Print source statistics
            print("\nSource Statistics:")
            for url, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
                source_name = url.split('/')[-1]
                print(f"  {source_name}: {count} proxies")
            
            return unique_proxies

def print_results_summary(results: List[ProxyTestResult], metrics: TestMetrics):
    """Print a formatted summary of test results"""
    print("\n" + "="*60)
    print("PROXY TEST RESULTS SUMMARY")
    print("="*60)
    
    print(f"\n📊 Overall Metrics:")
    print(f"  Total Tested: {metrics.total_tested}")
    print(f"  Working: {metrics.working_count}")
    print(f"  Success Rate: {metrics.success_rate:.1f}%")
    print(f"  Avg Response Time: {metrics.average_response_time:.0f} ms")
    print(f"  Median Response Time: {metrics.median_response_time:.0f} ms")
    
    if metrics.anonymity_distribution:
        print(f"\n🕵️  Anonymity Distribution:")
        for anonymity, count in metrics.anonymity_distribution.items():
            percentage = (count / metrics.working_count * 100) if metrics.working_count > 0 else 0
            print(f"  {anonymity.title()}: {count} ({percentage:.1f}%)")
    
    if metrics.type_distribution:
        print(f"\n🔧 Proxy Type Distribution:")
        for proxy_type, count in metrics.type_distribution.items():
            percentage = (count / metrics.working_count * 100) if metrics.working_count > 0 else 0
            print(f"  {proxy_type.title()}: {count} ({percentage:.1f}%)")
    
    if metrics.top_countries:
        print(f"\n🌍 Top Countries:")
        for country, count in metrics.top_countries:
            percentage = (count / metrics.working_count * 100) if metrics.working_count > 0 else 0
            print(f"  {country}: {count} ({percentage:.1f}%)")
    
    # Show top 10 fastest working proxies
    working_proxies = sorted(
        [r for r in results if r.is_working],
        key=lambda x: x.response_time_ms
    )[:10]
    
    if working_proxies:
        print(f"\n⚡ Top 10 Fastest Proxies:")
        for i, result in enumerate(working_proxies, 1):
            print(f"  {i:2}. {result.proxy:20} {result.response_time_ms:5.0f} ms - {result.anonymity.value} - {result.proxy_type.value}")
    
    # Show proxy failure reasons
    failed_proxies = [r for r in results if not r.is_working]
    if failed_proxies:
        error_counts = {}
        for result in failed_proxies:
            error = result.error_message or "Unknown error"
            error_counts[error] = error_counts.get(error, 0) + 1
        
        print(f"\n❌ Common Failure Reasons:")
        for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            percentage = (count / len(failed_proxies) * 100)
            print(f"  {error}: {count} ({percentage:.1f}%)")

async def main():
    """Main testing routine"""
    print("Proxy Testing Framework")
    print("=" * 40)
    
    # Step 1: Fetch proxies from GitHub sources
    fetcher = ProxySourceFetcher()
    proxies = await fetcher.fetch_all_sources()
    
    if not proxies:
        print("\n❌ No proxies found from any source!")
        return
    
    # Step 2: Test proxies
    print(f"\n🚀 Starting proxy validation...")
    tester = ProxyTester(max_concurrent_tests=50, timeout=10.0)
    
    # Test all proxies
    results = await tester.test_batch(proxies)
    
    # Step 3: Calculate metrics
    metrics = tester.get_metrics()
    
    # Step 4: Print summary
    print_results_summary(results, metrics)
    
    # Step 5: Save results
    tester.save_results("proxy_test_results.json")
    
    # Step 6: Export working proxies to text file
    working_proxies = [r.proxy for r in results if r.is_working]
    if working_proxies:
        with open("working_proxies.txt", "w") as f:
            for proxy in working_proxies:
                f.write(f"{proxy}\n")
        print(f"\n💾 Working proxies saved to 'working_proxies.txt' ({len(working_proxies)} proxies)")
    
    # Step 7: Recommendations
    print(f"\n🎯 Recommendations:")
    if metrics.success_rate < 10:
        print("  ⚠️  Low success rate. Consider:")
        print("     • Using paid proxy services for better reliability")
        print("     • Testing at different times (proxy lists update frequently)")
        print("     • Adding more proxy sources")
    elif metrics.success_rate < 30:
        print("  ⚡ Moderate success rate. For better performance:")
        print("     • Use the fastest proxies from the top 10 list")
        print("     • Implement proxy rotation to avoid overuse")
        print("     • Consider adding residential proxy sources")
    else:
        print("  ✅ Good success rate! You can:")
        print("     • Use these proxies for light automation tasks")
        print("     • Implement proper rotation and error handling")
        print("     • Monitor proxy performance over time")
    
    print(f"\n✅ Testing complete!")

if __name__ == "__main__":
    asyncio.run(main())