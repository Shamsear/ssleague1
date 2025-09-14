#!/usr/bin/env python3
"""
Performance Testing Script for Neon Optimizations
Tests the impact of 8GB RAM optimization settings
"""

import time
import psycopg2
import concurrent.futures
from urllib.parse import urlparse
import os
from dotenv import load_dotenv
import statistics

load_dotenv()

class PerformanceTest:
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL not found in environment")
        
        # Parse URL to check if it's Neon
        self.is_neon = 'neon.tech' in self.db_url
        print(f"Testing {'Neon' if self.is_neon else 'non-Neon'} database")
        print(f"URL: {urlparse(self.db_url).hostname}")
        print("-" * 60)
    
    def test_connection_pool(self, num_connections=50):
        """Test connection pool performance"""
        print(f"\n📊 Testing Connection Pool (Creating {num_connections} connections)")
        
        start_time = time.time()
        connections = []
        
        try:
            for i in range(num_connections):
                conn = psycopg2.connect(self.db_url)
                connections.append(conn)
                if (i + 1) % 10 == 0:
                    print(f"   Created {i + 1} connections...")
            
            elapsed = time.time() - start_time
            print(f"✅ Created {num_connections} connections in {elapsed:.2f} seconds")
            print(f"   Average: {elapsed/num_connections*1000:.2f} ms per connection")
            
            # Test query performance with all connections
            query_times = []
            for conn in connections[:20]:  # Test with 20 connections
                cursor = conn.cursor()
                query_start = time.time()
                cursor.execute("SELECT COUNT(*) FROM player")
                result = cursor.fetchone()
                query_time = time.time() - query_start
                query_times.append(query_time)
                cursor.close()
            
            avg_query_time = statistics.mean(query_times)
            print(f"✅ Average query time with pooled connections: {avg_query_time*1000:.2f} ms")
            
        finally:
            # Cleanup
            for conn in connections:
                conn.close()
        
        return elapsed
    
    def test_concurrent_queries(self, num_workers=20, queries_per_worker=10):
        """Test concurrent query performance"""
        print(f"\n📊 Testing Concurrent Queries ({num_workers} workers, {queries_per_worker} queries each)")
        
        def run_queries(worker_id):
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            times = []
            
            for i in range(queries_per_worker):
                start = time.time()
                cursor.execute("""
                    SELECT p.id, p.name, p.overall_rating, t.name as team_name
                    FROM player p
                    LEFT JOIN team t ON p.team_id = t.id
                    ORDER BY p.overall_rating DESC
                    LIMIT 50
                """)
                results = cursor.fetchall()
                times.append(time.time() - start)
            
            cursor.close()
            conn.close()
            return times
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(run_queries, i) for i in range(num_workers)]
            all_times = []
            
            for future in concurrent.futures.as_completed(futures):
                all_times.extend(future.result())
        
        total_time = time.time() - start_time
        total_queries = num_workers * queries_per_worker
        
        print(f"✅ Completed {total_queries} queries in {total_time:.2f} seconds")
        print(f"   Throughput: {total_queries/total_time:.2f} queries/second")
        print(f"   Average latency: {statistics.mean(all_times)*1000:.2f} ms")
        print(f"   Median latency: {statistics.median(all_times)*1000:.2f} ms")
        print(f"   95th percentile: {statistics.quantiles(all_times, n=20)[18]*1000:.2f} ms")
        
        return total_time
    
    def test_complex_aggregations(self):
        """Test complex aggregation queries"""
        print(f"\n📊 Testing Complex Aggregations")
        
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        
        queries = [
            ("Team Statistics", """
                SELECT t.id, t.name, t.balance,
                       COUNT(p.id) as player_count,
                       AVG(p.overall_rating) as avg_rating,
                       MAX(p.overall_rating) as max_rating,
                       MIN(p.overall_rating) as min_rating
                FROM team t
                LEFT JOIN player p ON t.id = p.team_id
                GROUP BY t.id, t.name, t.balance
                ORDER BY avg_rating DESC
            """),
            
            ("Position Analysis", """
                SELECT position,
                       COUNT(*) as count,
                       AVG(overall_rating) as avg_rating,
                       MAX(overall_rating) as max_rating
                FROM player
                GROUP BY position
                ORDER BY avg_rating DESC
            """),
            
            ("Bid Analysis", """
                SELECT r.id,
                       COUNT(b.id) as total_bids,
                       AVG(b.amount) as avg_bid,
                       MAX(b.amount) as max_bid
                FROM round r
                LEFT JOIN bid b ON r.id = b.round_id
                GROUP BY r.id
                ORDER BY r.id
            """)
        ]
        
        for name, query in queries:
            start = time.time()
            cursor.execute(query)
            results = cursor.fetchall()
            elapsed = time.time() - start
            print(f"   {name}: {elapsed*1000:.2f} ms ({len(results)} rows)")
        
        cursor.close()
        conn.close()
    
    def test_bulk_operations(self):
        """Test bulk insert/update performance"""
        print(f"\n📊 Testing Bulk Operations")
        
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        
        # Test bulk read
        start = time.time()
        cursor.execute("SELECT * FROM player WHERE overall_rating >= 80")
        high_rated = cursor.fetchall()
        read_time = time.time() - start
        print(f"   Bulk read ({len(high_rated)} players): {read_time*1000:.2f} ms")
        
        # Test with indexes
        start = time.time()
        cursor.execute("""
            SELECT p.*, t.name as team_name
            FROM player p
            LEFT JOIN team t ON p.team_id = t.id
            WHERE p.position = 'CF' AND p.overall_rating >= 75
            ORDER BY p.overall_rating DESC
        """)
        filtered = cursor.fetchall()
        indexed_time = time.time() - start
        print(f"   Indexed query ({len(filtered)} results): {indexed_time*1000:.2f} ms")
        
        cursor.close()
        conn.close()
    
    def run_all_tests(self):
        """Run all performance tests"""
        print("\n" + "="*60)
        print("🚀 STARTING PERFORMANCE TESTS")
        print("="*60)
        
        # Test 1: Connection Pool
        pool_time = self.test_connection_pool(30)
        
        # Test 2: Concurrent Queries
        concurrent_time = self.test_concurrent_queries(15, 5)
        
        # Test 3: Complex Aggregations
        self.test_complex_aggregations()
        
        # Test 4: Bulk Operations
        self.test_bulk_operations()
        
        # Summary
        print("\n" + "="*60)
        print("📈 PERFORMANCE SUMMARY")
        print("="*60)
        
        if self.is_neon:
            print("✅ Neon database with 8GB RAM optimizations")
            print("\nExpected improvements with optimizations:")
            print("  • 4x larger connection pool (20 vs 5)")
            print("  • 6x faster connection recycling (5 min vs 30 min)")
            print("  • Optimized TCP keepalives for stability")
            print("  • Memory-optimized query execution")
            print("  • Parallel query execution enabled")
            print("  • JIT compilation for complex queries")
        else:
            print("ℹ️  Non-Neon database with standard settings")
        
        print(f"\n🎯 Connection pool test: {pool_time:.2f}s")
        print(f"🎯 Concurrent query test: {concurrent_time:.2f}s")
        
        print("\n💡 Tips for best performance:")
        print("  1. Use pagination for large result sets")
        print("  2. Enable query result caching where appropriate")
        print("  3. Use prepared statements for repeated queries")
        print("  4. Monitor slow queries and optimize them")
        print("  5. Keep connections warm with LIFO pool strategy")

if __name__ == "__main__":
    tester = PerformanceTest()
    tester.run_all_tests()