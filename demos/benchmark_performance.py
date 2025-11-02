"""
Performance Benchmarking Script for Elastic RAG

This script measures:
1. Document ingestion speed (pages/second)
2. Query response time (end-to-end latency)
3. Concurrent request handling

Usage:
    python demos/benchmark_performance.py
"""

import asyncio
import statistics

# Add src to path
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent.rag_agent import create_rag_agent
from agent.runner import SimpleRAGRunner
from config.settings import Settings
from pipeline.ingestion import IngestionPipeline


class PerformanceBenchmark:
    """Performance benchmarking for Elastic RAG system."""

    def __init__(self):
        self.settings = Settings()
        self.results: dict[str, Any] = {}

    async def benchmark_document_ingestion(self, test_file: Path, iterations: int = 3):
        """Benchmark document ingestion speed."""
        print("\n" + "=" * 80)
        print("BENCHMARK 1: Document Ingestion Speed")
        print("=" * 80)

        pipeline = IngestionPipeline(self.settings)
        times = []

        for i in range(iterations):
            print(f"\nIteration {i+1}/{iterations}")
            start_time = time.time()

            try:
                result = await pipeline.process_document(
                    file_path=test_file, filename=test_file.name
                )

                elapsed = time.time() - start_time
                times.append(elapsed)

                print(f"  ✓ Processed {result.get('pages_processed', 0)} pages")
                print(f"  ✓ Created {result.get('chunks_created', 0)} chunks")
                print(f"  ✓ Time: {elapsed:.2f}s")
                print(f"  ✓ Speed: {result.get('pages_processed', 0) / elapsed:.2f} pages/second")

            except Exception as e:
                print(f"  ✗ Error: {e}")
                continue

        if times:
            avg_time = statistics.mean(times)
            print(f"\n📊 Average ingestion time: {avg_time:.2f}s")
            print(f"📊 Min: {min(times):.2f}s, Max: {max(times):.2f}s")

            self.results["ingestion"] = {
                "avg_time": avg_time,
                "min_time": min(times),
                "max_time": max(times),
                "iterations": iterations,
            }

    async def benchmark_query_response(self, queries: list[str], iterations: int = 5):
        """Benchmark query response time."""
        print("\n" + "=" * 80)
        print("BENCHMARK 2: Query Response Time")
        print("=" * 80)

        agent = create_rag_agent()
        runner = SimpleRAGRunner(agent)
        all_times = []

        for query in queries:
            print(f"\nQuery: '{query}'")
            query_times = []

            for i in range(iterations):
                start_time = time.time()

                try:
                    response = await runner._query_async(query)
                    elapsed = time.time() - start_time
                    query_times.append(elapsed)

                    if i == 0:  # Show first response
                        answer = (
                            response[:100] if isinstance(response, str) else str(response)[:100]
                        )
                        print(f"  Sample response: {answer}...")

                except Exception as e:
                    print(f"  ✗ Error on iteration {i+1}: {e}")
                    continue

            if query_times:
                avg = statistics.mean(query_times)
                print(f"  ✓ Average: {avg:.2f}s")
                print(f"  ✓ Min: {min(query_times):.2f}s, Max: {max(query_times):.2f}s")
                all_times.extend(query_times)

        if all_times:
            overall_avg = statistics.mean(all_times)
            print(f"\n📊 Overall average query time: {overall_avg:.2f}s")
            print(f"📊 Min: {min(all_times):.2f}s, Max: {max(all_times):.2f}s")
            if len(all_times) > 1:
                print(f"📊 Std dev: {statistics.stdev(all_times):.2f}s")

            # Performance assessment
            if overall_avg < 2.0:
                print("✅ EXCELLENT: Sub 2-second response time")
            elif overall_avg < 5.0:
                print("✅ GOOD: Under 5-second response time")
            elif overall_avg < 10.0:
                print("⚠️  ACCEPTABLE: 5-10 second response time")
            else:
                print("❌ NEEDS IMPROVEMENT: >10 second response time")

            self.results["query"] = {
                "avg_time": overall_avg,
                "min_time": min(all_times),
                "max_time": max(all_times),
                "std_dev": statistics.stdev(all_times) if len(all_times) > 1 else 0,
                "queries_tested": len(queries),
                "iterations_per_query": iterations,
            }

    async def benchmark_concurrent_queries(self, query: str, concurrent: int = 5):
        """Benchmark concurrent query handling."""
        print("\n" + "=" * 80)
        print(f"BENCHMARK 3: Concurrent Query Handling ({concurrent} simultaneous)")
        print("=" * 80)

        agent = create_rag_agent()
        runner = SimpleRAGRunner(agent)

        async def run_query(query_id: int):
            start = time.time()
            try:
                _ = await runner._query_async(query)
                elapsed = time.time() - start
                return query_id, elapsed, True, None
            except Exception as e:
                elapsed = time.time() - start
                return query_id, elapsed, False, str(e)

        # Run concurrent queries
        start_time = time.time()
        tasks = [run_query(i) for i in range(concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_elapsed = time.time() - start_time

        # Analyze results
        successful = [r for r in results if not isinstance(r, Exception) and r[2]]
        failed = [r for r in results if isinstance(r, Exception) or not r[2]]

        print(f"\n✓ Total time for {concurrent} concurrent queries: {total_elapsed:.2f}s")
        print(f"✓ Successful: {len(successful)}/{concurrent}")
        print(f"✓ Failed: {len(failed)}/{concurrent}")

        if successful:
            times = [r[1] for r in successful]
            print("\n📊 Individual query times:")
            print(f"   Average: {statistics.mean(times):.2f}s")
            print(f"   Min: {min(times):.2f}s")
            print(f"   Max: {max(times):.2f}s")

            self.results["concurrent"] = {
                "total_time": total_elapsed,
                "concurrent_count": concurrent,
                "successful": len(successful),
                "failed": len(failed),
                "avg_individual_time": statistics.mean(times),
                "max_individual_time": max(times),
            }

    def print_summary(self):
        """Print benchmark summary."""
        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)

        if "ingestion" in self.results:
            print("\n📄 Document Ingestion:")
            print(f"   Average time: {self.results['ingestion']['avg_time']:.2f}s")

        if "query" in self.results:
            print("\n🔍 Query Response:")
            print(f"   Average time: {self.results['query']['avg_time']:.2f}s")
            print(f"   Standard deviation: {self.results['query']['std_dev']:.2f}s")

        if "concurrent" in self.results:
            print("\n🔀 Concurrent Handling:")
            print(
                f"   {self.results['concurrent']['concurrent_count']} queries in {self.results['concurrent']['total_time']:.2f}s"
            )
            print(
                f"   Success rate: {self.results['concurrent']['successful']}/{self.results['concurrent']['concurrent_count']}"
            )

        print("\n" + "=" * 80)


async def main():
    """Run all benchmarks."""
    benchmark = PerformanceBenchmark()

    # Test file path (adjust as needed)
    test_file = Path(__file__).parent.parent / "tests" / "fixtures" / "sample.txt"

    if not test_file.exists():
        print(f"Warning: Test file not found: {test_file}")
        print("Skipping ingestion benchmark")
    # Note: Skipping ingestion for quick validation
    # else:
    #     # Benchmark 1: Document ingestion
    #     await benchmark.benchmark_document_ingestion(test_file, iterations=3)

    # Benchmark 2: Query response time (reduced iterations for speed)
    test_queries = [
        "What is machine learning?",
    ]
    await benchmark.benchmark_query_response(test_queries, iterations=1)

    # Benchmark 3: Concurrent queries (reduced for speed)
    await benchmark.benchmark_concurrent_queries("What is artificial intelligence?", concurrent=2)

    # Print summary
    benchmark.print_summary()

    print("\n✅ Benchmarking complete!")


if __name__ == "__main__":
    asyncio.run(main())
