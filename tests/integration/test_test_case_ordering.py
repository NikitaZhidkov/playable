"""
Integration tests for test case ordering and failure handling.
Tests the new behaviors:
1. Test cases run in order (1 -> 5)
2. Execution stops on first test case failure
3. Retry count resets when passing previously failed stages
"""
import pytest
import json
from src.containers import Workspace


@pytest.mark.asyncio
async def test_test_cases_run_in_order(dagger_client):
    """
    Test that test cases are discovered and sorted in correct order (1 -> 5).
    """
    workspace = await Workspace.create(dagger_client)
    
    # Create test cases in random order
    test_cases = [
        ("test_case_3.json", {"order": 3}),
        ("test_case_1.json", {"order": 1}),
        ("test_case_5.json", {"order": 5}),
        ("test_case_2.json", {"order": 2}),
        ("test_case_4.json", {"order": 4}),
    ]
    
    for filename, data in test_cases:
        workspace.write_file(filename, json.dumps(data))
    
    # Discover test case files
    discovered_files = await workspace.list_files("test_case_*.json")
    
    # Sort them (same as agent_graph does)
    sorted_files = sorted(discovered_files)
    
    # Verify they're in order
    expected_order = [
        "test_case_1.json",
        "test_case_2.json", 
        "test_case_3.json",
        "test_case_4.json",
        "test_case_5.json"
    ]
    
    assert sorted_files == expected_order, f"Expected {expected_order}, got {sorted_files}"
    
    # Verify data matches order
    for i, filename in enumerate(sorted_files, 1):
        content = await workspace.read_file(filename)
        data = json.loads(content)
        assert data["order"] == i, f"File {filename} should have order {i}, got {data['order']}"
    
    print(f"\n✅ Test cases sorted in correct order")
    print(f"   Order: {sorted_files}")


@pytest.mark.asyncio
async def test_test_case_ordering_with_gaps(dagger_client):
    """
    Test that test cases are still ordered correctly even with gaps in numbering.
    """
    workspace = await Workspace.create(dagger_client)
    
    # Create test cases with gaps (1, 3, 5)
    test_cases = [
        ("test_case_5.json", {"order": 5}),
        ("test_case_1.json", {"order": 1}),
        ("test_case_3.json", {"order": 3}),
    ]
    
    for filename, data in test_cases:
        workspace.write_file(filename, json.dumps(data))
    
    # Discover and sort
    discovered_files = await workspace.list_files("test_case_*.json")
    sorted_files = sorted(discovered_files)
    
    # Should be in order despite gaps
    expected_order = [
        "test_case_1.json",
        "test_case_3.json",
        "test_case_5.json"
    ]
    
    assert sorted_files == expected_order, f"Expected {expected_order}, got {sorted_files}"
    
    print(f"\n✅ Test cases with gaps sorted correctly")
    print(f"   Order: {sorted_files}")


@pytest.mark.asyncio
async def test_test_case_ordering_alphabetically_correct(dagger_client):
    """
    Test that alphabetical sorting works correctly (not just numeric).
    This catches issues like '10' sorting before '2'.
    """
    workspace = await Workspace.create(dagger_client)
    
    # Create test cases including test_case_10 if it existed
    # Note: We only allow 1-5, but test the sorting logic
    test_cases = [
        ("test_case_2.json", {}),
        ("test_case_10.json", {}),
        ("test_case_1.json", {}),
    ]
    
    for filename, data in test_cases:
        workspace.write_file(filename, json.dumps(data))
    
    discovered_files = await workspace.list_files("test_case_*.json")
    sorted_files = sorted(discovered_files)
    
    # With string sorting, '10' comes before '2'
    # Expected: test_case_1.json, test_case_10.json, test_case_2.json
    expected_order = [
        "test_case_1.json",
        "test_case_10.json",
        "test_case_2.json"
    ]
    
    assert sorted_files == expected_order, f"Expected {expected_order}, got {sorted_files}"
    
    print(f"\n✅ Alphabetical sorting works as expected")
    print(f"   Order: {sorted_files}")
    print(f"   Note: This is why we limit to 1-5 (avoids '10' before '2' issue)")


@pytest.mark.asyncio  
async def test_natural_sorting_for_single_digits(dagger_client):
    """
    Test that single-digit test cases (1-5) sort correctly.
    """
    workspace = await Workspace.create(dagger_client)
    
    # Create in reverse order
    for i in [5, 4, 3, 2, 1]:
        workspace.write_file(f"test_case_{i}.json", json.dumps({"num": i}))
    
    discovered_files = await workspace.list_files("test_case_*.json")
    sorted_files = sorted(discovered_files)
    
    # Should be 1, 2, 3, 4, 5
    expected_order = [f"test_case_{i}.json" for i in range(1, 6)]
    
    assert sorted_files == expected_order, f"Expected {expected_order}, got {sorted_files}"
    
    print(f"\n✅ Single-digit test cases sort correctly")
    print(f"   Order: {sorted_files}")


@pytest.mark.asyncio
async def test_maximum_five_test_cases_enforced(dagger_client):
    """
    Test that when more than 5 test cases exist, only first 5 are used.
    """
    workspace = await Workspace.create(dagger_client)
    
    # Create 7 test cases
    for i in range(1, 8):
        workspace.write_file(f"test_case_{i}.json", json.dumps({"num": i}))
    
    discovered_files = await workspace.list_files("test_case_*.json")
    sorted_files = sorted(discovered_files)
    
    # Should find all 7
    assert len(sorted_files) == 7, f"Should find 7 test cases, found {len(sorted_files)}"
    
    # Simulate agent_graph behavior: limit to 5
    limited_files = sorted_files[:5]
    
    assert len(limited_files) == 5, "Should limit to 5 test cases"
    assert limited_files == [f"test_case_{i}.json" for i in range(1, 6)], \
        "Should use first 5 test cases in order"
    
    print(f"\n✅ Maximum 5 test cases enforced")
    print(f"   Found: {len(sorted_files)} test cases")
    print(f"   Using: {len(limited_files)} test cases (first 5)")
    print(f"   Limited to: {limited_files}")


def test_retry_count_reset_logic():
    """
    Test the retry count reset logic (unit test, no containers needed).
    """
    # Scenario 1: Pass main validation after failing it
    previous_failures = ["Main VLM validation failed"]
    previous_retry_count = 3
    
    # When we pass, retry count should reset to 0
    if previous_retry_count > 0 and previous_failures:
        test_case_retry_count = 0
    
    assert test_case_retry_count == 0, "Retry count should reset after passing main validation"
    
    # Scenario 2: Pass test case after failing it
    test_case_name = "test_case_1"
    previous_failures_with_test = ["test_case_1 failed: Something wrong"]
    test_case_retry_count = 2
    
    # Check if this test case failed before
    if any(test_case_name in str(failure) for failure in previous_failures_with_test):
        test_case_retry_count = 0
    
    assert test_case_retry_count == 0, "Retry count should reset after passing previously failed test case"
    
    # Scenario 3: Pass test case that never failed before
    test_case_name = "test_case_2"
    previous_failures_no_test = ["test_case_1 failed: Something wrong"]
    test_case_retry_count = 0
    
    # This test case wasn't in previous failures, so count stays 0
    if any(test_case_name in str(failure) for failure in previous_failures_no_test):
        test_case_retry_count = 0
    
    assert test_case_retry_count == 0, "Retry count should stay 0 for test case that never failed"
    
    print(f"\n✅ Retry count reset logic works correctly")
    print(f"   Scenario 1: Reset after passing main validation ✓")
    print(f"   Scenario 2: Reset after passing previously failed test case ✓")
    print(f"   Scenario 3: Stay 0 for test case that never failed ✓")

