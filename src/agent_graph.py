from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from src.agent_state import AgentState
from src.llm_client import LLMClient
from src.tools import FileOperations
from src.custom_types import ToolUse, TextRaw
from test_game import validate_game_in_workspace, validate_game_with_test_case, TEST_SCRIPT
from src.vlm import (
    VLMClient,
    validate_playable_with_vlm,
    validate_test_case_with_vlm,
    save_test_case_error,
    VLM_PLAYABLE_VALIDATION_PROMPT,
    VLM_TEST_CASE_VALIDATION_PROMPT
)
from src.prompts import (
    FEEDBACK_CONTINUE_TASK,
    FEEDBACK_VALIDATION_FAILED,
    SYSTEM_PIXI_GAME_DEVELOPER_PROMPT,
    SYSTEM_PIXI_FEEDBACK_PROMPT,
    PIXI_CDN_INSTRUCTIONS,
    ASSET_PACK_INSTRUCTIONS
)
from langfuse.decorators import observe, langfuse_context
import logging

logger = logging.getLogger(__name__)

# Flag to control whether to use interactive mode (human can respond to LLM questions)
INTERACTIVE_MODE = True


def create_agent_graph(llm_client: LLMClient, file_ops: FileOperations):
    """Create the LangGraph agent workflow."""
    
    @observe(name="llm_node")
    async def llm_node(state: AgentState) -> dict:
        """Call the LLM with current state."""
        logger.info("=== LLM Node ===")
        
        # Determine which system prompt to use
        is_feedback = state.get("is_feedback_mode", False)
        retry_count = state.get("retry_count", 0)
        
        if is_feedback:
            logger.info("Using FEEDBACK mode system prompt")
            system_prompt = SYSTEM_PIXI_FEEDBACK_PROMPT + "\n\n" + PIXI_CDN_INSTRUCTIONS
            mode = "feedback"
        else:
            logger.info("Using CREATION mode system prompt")
            system_prompt = SYSTEM_PIXI_GAME_DEVELOPER_PROMPT + "\n\n" + PIXI_CDN_INSTRUCTIONS
            mode = "creation"
        
        # Add asset pack context if available
        asset_context = state.get("asset_context")
        if asset_context:
            logger.info("Adding asset pack context to system prompt")
            asset_instructions = ASSET_PACK_INSTRUCTIONS.format(asset_context=asset_context)
            system_prompt = system_prompt + "\n\n" + asset_instructions
        
        # Update Langfuse context with metadata and tags
        langfuse_context.update_current_observation(
            metadata={
                "mode": mode,
                "retry_count": retry_count,
                "has_asset_context": bool(asset_context),
                "message_count": len(state["messages"]),
                "session_id": state.get("session_id")
            },
            tags=[mode, f"retry_{retry_count}"]
        )
        
        # Get tools from file operations
        tools = file_ops.tools
        
        # Call LLM with appropriate system prompt
        response = llm_client.call(
            messages=state["messages"],
            tools=tools,
            system=system_prompt
        )
        
        # Parse response
        parsed_content = llm_client.parse_anthropic_response(response)
        
        # Extract text and tool calls
        text_parts = []
        tool_calls = []
        
        for item in parsed_content:
            if isinstance(item, TextRaw):
                text_parts.append(item.text)
                logger.info(f"LLM: {item.text[:200]}...")
            elif isinstance(item, ToolUse):
                tool_calls.append({
                    "name": item.name,
                    "args": item.input,
                    "id": item.id
                })
                logger.info(f"Tool call: {item.name}")
        
        # Create AI message
        ai_message = AIMessage(
            content="\n".join(text_parts) if text_parts else "",
            tool_calls=tool_calls
        )
        
        # Store parsed content for tools node
        return {
            "messages": [ai_message],
            "_parsed_content": parsed_content
        }
    
    @observe(name="tools_node")
    async def tools_node(state: AgentState) -> dict:
        """Execute tool calls."""
        logger.info("=== Tools Node ===")
        
        # Get parsed content from previous node
        parsed_content = state.get("_parsed_content", [])
        
        # Execute tools
        tool_results, is_completed = await file_ops.run_tools(parsed_content)
        
        # Convert to tool messages
        tool_messages = []
        for tool_result in tool_results:
            tool_messages.append(
                ToolMessage(
                    content=tool_result.tool_result.content,
                    tool_call_id=tool_result.tool_result.tool_use_id or "",
                    name=tool_result.tool_result.name or ""
                )
            )
            logger.info(
                f"Tool result for {tool_result.tool_result.name}: "
                f"{tool_result.tool_result.content[:100]}..."
            )
        
        # Return updated state with modified workspace
        logger.info(f"=== Tools Node Complete - Returning updated workspace ===")
        return {
            "messages": tool_messages,
            "is_completed": is_completed,
            "workspace": file_ops.workspace  # Propagate workspace changes back to state
        }
    
    async def human_input_node(state: AgentState) -> dict:
        """Get input from human user."""
        logger.info("=== Human Input Node ===")
        
        # Get the last AI message
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.content:
            print("\n" + "=" * 60)
            print("🤖 Agent says:")
            print(last_message.content)
            print("=" * 60)
        
        # Get user response
        user_input = input("\n👤 Your response (or press Enter to skip): ").strip()
        
        if user_input:
            logger.info(f"User provided response: {user_input[:100]}...")
            return {
                "messages": [HumanMessage(content=user_input)]
            }
        else:
            # User skipped, tell LLM to continue without user input
            logger.info("User skipped input, asking LLM to continue")
            return {
                "messages": [HumanMessage(content=FEEDBACK_CONTINUE_TASK)]
            }
    
    @observe(name="test_node")
    async def test_node(state: AgentState) -> dict:
        """Test the generated game in a browser and validate with VLM."""
        logger.info("=== Test Node ===")
        
        # Initialize VLM client
        vlm_client = VLMClient()
        
        # Create test run ID for this validation run - all debug files will go here
        from datetime import datetime
        test_run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info(f"Test run ID: {test_run_id}")

        # Prepare Playwright container with game files
        logger.info("Preparing Playwright container with game files...")
        playwright_container = state["playwright_container"]
        playwright_container.reset()  # Reset to clean state
        playwright_container.copy_directory(
            state["workspace"].container().directory(".")
        ).with_test_script(TEST_SCRIPT)
        
        # Run browser tests to get screenshot and console logs
        logger.info("Running browser tests on generated game...")
        test_result = await validate_game_in_workspace(playwright_container)
        
        # Validate with VLM
        logger.info("Validating playable with VLM...")
        is_feedback_mode = state.get("is_feedback_mode", False)
        is_valid, reason = validate_playable_with_vlm(
            vlm_client=vlm_client,
            screenshot_bytes=test_result.screenshot_bytes,
            console_logs=test_result.console_logs,
            user_prompt=state.get("task_description", ""),
            template_str=VLM_PLAYABLE_VALIDATION_PROMPT,
            session_id=state.get("session_id"),
            is_feedback_mode=is_feedback_mode,
            original_prompt=state.get("original_prompt", "") if is_feedback_mode else None,
            test_run_id=test_run_id
        )
        
        if not is_valid:
            logger.warning(f"❌ VLM validation failed: {reason}")
            # Increment retry count
            current_retry = state.get("retry_count", 0) + 1
            logger.info(f"Retry attempt {current_retry}/5")
            
            # Format console logs for feedback
            if test_result.console_logs:
                console_logs_formatted = "  " + "\n  ".join(test_result.console_logs)
            else:
                console_logs_formatted = "  No console logs captured."
            
            # Create feedback message for LLM with VLM reason and console logs
            feedback_message = HumanMessage(
                content=FEEDBACK_VALIDATION_FAILED.format(
                    reason=reason,
                    console_logs=console_logs_formatted
                )
            )
            
            return {
                "messages": [feedback_message],
                "test_failures": [reason],
                "retry_count": current_retry,
                "is_completed": False,  # Reset completion flag to retry
            }
        
        # Main VLM validation passed!
        logger.info("✅ VLM validation passed! Game is correct.")
        
        # Check if we previously failed main validation - if so, reset retry count
        previous_failures = state.get("test_failures", [])
        previous_retry_count = state.get("retry_count", 0)
        
        # Reset retry count to 0 since we passed main validation
        # This applies whether we're starting test case validation for the first time
        # or if we previously failed main validation and now passed
        if previous_retry_count > 0 and previous_failures:
            logger.info(f"Main VLM validation passed after {previous_retry_count} previous failures - resetting retry count")
        else:
            logger.info("Main VLM validation passed - starting test case validation")
        
        test_case_retry_count = 0
        
        # Now run test case validation
        logger.info("=== Running Test Case Validation ===")
        
        # Discover test case files (at root level)
        try:
            test_case_files = await state["workspace"].list_files("test_case_*.json")
            # Sort test cases to ensure they run in order (1 -> 5)
            test_case_files = sorted(test_case_files)
            logger.info(f"Found {len(test_case_files)} test case files (sorted): {test_case_files}")
        except Exception as e:
            logger.error(f"Error discovering test case files: {e}")
            test_case_files = []
        
        # Validate test case count (require 1-5)
        if len(test_case_files) == 0:
            logger.error("❌ No test cases found! At least 1 test case is required.")
            test_case_retry_count += 1
            feedback_message = HumanMessage(
                content="Test case validation failed: No test cases found. You must create 1-5 test cases at the ROOT level (test_case_1.json through test_case_5.json, same directory as index.html)."
            )
            return {
                "messages": [feedback_message],
                "test_failures": ["Missing test cases (required: 1-5)"],
                "retry_count": test_case_retry_count,
                "is_completed": False,
            }
        
        if len(test_case_files) > 5:
            logger.warning(f"Found {len(test_case_files)} test cases, but maximum is 5. Using first 5.")
            test_case_files = test_case_files[:5]
        
        # Run each test case in order (1 -> 5)
        # Stop on first failure to save time
        for test_case_file in test_case_files:
            test_case_name = test_case_file.split('/')[-1].replace('.json', '')
            logger.info(f"Running test case: {test_case_name}")
            
            try:
                # Read test case JSON from workspace
                test_case_json = await state["workspace"].read_file(test_case_file)
                import json
                test_case_data = json.loads(test_case_json)
                
                # Extract expected output
                expected_output = test_case_data.get("expectedOutput", "")
                if not expected_output:
                    logger.warning(f"Test case {test_case_name} missing 'expectedOutput' field")
                    failure_msg = f"{test_case_name}: Missing 'expectedOutput' field in test case JSON"
                    
                    # Save test case error for debugging
                    save_test_case_error(
                        test_case_name=test_case_name,
                        expected_output="(missing)",
                        actual_output="N/A - test case validation error",
                        error_message=failure_msg,
                        session_id=state.get("session_id"),
                        test_run_id=test_run_id
                    )
                    
                    # Increment retry count and return immediately
                    test_case_retry_count += 1
                    feedback_message = HumanMessage(
                        content=f"Test case validation failed: {failure_msg}\n\nPlease fix the test case and try again."
                    )
                    
                    return {
                        "messages": [feedback_message],
                        "test_failures": [failure_msg],
                        "retry_count": test_case_retry_count,
                        "is_completed": False,
                    }
                
                # Prepare fresh Playwright container for this test case
                test_case_container = state["playwright_container"]
                test_case_container.reset()
                test_case_container.copy_directory(
                    state["workspace"].container().directory(".")
                )
                
                # Run test with test case loaded
                test_case_result = await validate_game_with_test_case(
                    container=test_case_container,
                    test_case_json=test_case_json,
                    test_case_name=test_case_name
                )
                
                # Check for errors in loading test case
                if test_case_result.errors:
                    logger.warning(f"Test case {test_case_name} had errors: {test_case_result.errors}")
                    failure_msg = f"{test_case_name}: {', '.join(test_case_result.errors)}"
                    
                    # Save test case error for debugging
                    save_test_case_error(
                        test_case_name=test_case_name,
                        expected_output=expected_output,
                        actual_output="N/A - test case loading error",
                        error_message=failure_msg + "\n\nErrors:\n" + "\n".join(test_case_result.errors),
                        session_id=state.get("session_id"),
                        test_run_id=test_run_id
                    )
                    
                    # Increment retry count and return immediately
                    test_case_retry_count += 1
                    feedback_message = HumanMessage(
                        content=f"Test case validation failed: {failure_msg}\n\nPlease fix the issues and try again."
                    )
                    
                    return {
                        "messages": [feedback_message],
                        "test_failures": [failure_msg],
                        "retry_count": test_case_retry_count,
                        "is_completed": False,
                    }
                
                # Validate with VLM
                is_test_case_valid, test_case_reason = validate_test_case_with_vlm(
                    vlm_client=vlm_client,
                    screenshot_bytes=test_case_result.screenshot_bytes,
                    expected_output=expected_output,
                    template_str=VLM_TEST_CASE_VALIDATION_PROMPT,
                    test_case_name=test_case_name,
                    session_id=state.get("session_id"),
                    test_case_json=test_case_json,
                    test_run_id=test_run_id
                )
                
                if is_test_case_valid:
                    logger.info(f"✅ Test case {test_case_name} passed")
                    # Test case passed - if we had previous failures on this test case, reset retry count
                    # Check if this test case failed before by looking at previous test_failures
                    previous_failures = state.get("test_failures", [])
                    if any(test_case_name in str(failure) for failure in previous_failures):
                        logger.info(f"Test case {test_case_name} passed after previous failure - resetting retry count")
                        test_case_retry_count = 0
                else:
                    logger.warning(f"❌ Test case {test_case_name} failed: {test_case_reason}")
                    failure_msg = f"{test_case_name} failed: Expected '{expected_output}' but VLM observed '{test_case_reason}'"
                    
                    # Save test case error for debugging
                    save_test_case_error(
                        test_case_name=test_case_name,
                        expected_output=expected_output,
                        actual_output=test_case_reason,
                        error_message=failure_msg,
                        session_id=state.get("session_id"),
                        test_run_id=test_run_id
                    )
                    
                    # Increment retry count and return immediately (stop executing other test cases)
                    test_case_retry_count += 1
                    logger.info(f"Test case retry attempt {test_case_retry_count}/5")
                    
                    feedback_message = HumanMessage(
                        content=f"Test case validation failed: {failure_msg}\n\nPlease fix the issues and update the test case if needed."
                    )
                    
                    return {
                        "messages": [feedback_message],
                        "test_failures": [failure_msg],
                        "retry_count": test_case_retry_count,
                        "is_completed": False,
                    }
                    
            except Exception as e:
                logger.error(f"Error running test case {test_case_name}: {e}", exc_info=True)
                failure_msg = f"{test_case_name}: Error running test case: {str(e)}"
                
                # Save test case error for debugging
                save_test_case_error(
                    test_case_name=test_case_name,
                    expected_output=expected_output if 'expected_output' in locals() else "(unknown)",
                    actual_output="N/A - exception occurred",
                    error_message=failure_msg + f"\n\nException:\n{str(e)}",
                    session_id=state.get("session_id"),
                    test_run_id=test_run_id
                )
                
                # Increment retry count and return immediately
                test_case_retry_count += 1
                feedback_message = HumanMessage(
                    content=f"Test case validation failed: {failure_msg}\n\nPlease fix the error and try again."
                )
                
                return {
                    "messages": [feedback_message],
                    "test_failures": [failure_msg],
                    "retry_count": test_case_retry_count,
                    "is_completed": False,
                }
        
        # All tests passed!
        logger.info("✅ All test cases passed! Game is fully validated.")
        
        # Move test cases to debug subfolder
        # Note: Keep MANIFEST.json at root for feedback context, only move test_case_*.json
        logger.info("Moving test cases to debug subfolder...")
        try:
            # Create debug_tests directory
            state["workspace"] = state["workspace"].write_file("debug_tests/.gitkeep", "", force=True)
            
            # Move only test case files to debug_tests/ (keep MANIFEST.json at root)
            for test_file in test_case_files:
                try:
                    # Read the file
                    content = await state["workspace"].read_file(test_file)
                    # Write to debug_tests/
                    state["workspace"] = state["workspace"].write_file(f"debug_tests/{test_file}", content, force=True)
                    # Delete original
                    state["workspace"] = state["workspace"].rm(test_file)
                    logger.info(f"Moved {test_file} to debug_tests/")
                except FileNotFoundError:
                    logger.warning(f"File {test_file} not found, skipping")
                except Exception as e:
                    logger.warning(f"Error moving {test_file}: {e}")
            
            logger.info("Test cases moved to debug_tests/ subfolder")
        except Exception as e:
            logger.warning(f"Error moving test cases to debug subfolder: {e}")
        
        return {
            "test_failures": [],
        }
    
    def should_continue(state: AgentState) -> str:
        """Decide whether to continue or end."""
        # Check if task is completed - route to tests
        if state.get("is_completed", False):
            logger.info("Task marked complete, routing to test node")
            return "test"
        
        # Check last message
        last_message = state["messages"][-1]
        
        # If last message has tool calls, go to tools node
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"
        
        # If last message is AI text without tool calls, and we're in interactive mode
        # go to human_input node so user can respond to LLM's question
        if isinstance(last_message, AIMessage) and INTERACTIVE_MODE:
            logger.info("LLM responded with text (possibly a question), going to human_input")
            return "human_input"
        
        # Otherwise end (no more work to do)
        logger.info("No tool calls and not interactive, ending workflow")
        return END
    
    def should_continue_after_tools(state: AgentState) -> str:
        """Decide whether to go to test or back to LLM after tools execution."""
        # If task is completed and tools succeeded, go to test
        if state.get("is_completed", False):
            logger.info("Task completed successfully, routing to test node")
            return "test"
        
        # Otherwise, continue with LLM
        logger.info("Tools executed, continuing with LLM")
        return "llm"
    
    def should_continue_after_test(state: AgentState) -> str:
        """Decide whether to retry after test failures or end."""
        test_failures = state.get("test_failures", [])
        retry_count = state.get("retry_count", 0)
        
        # If no test failures, we're done!
        if not test_failures:
            logger.info("Tests passed! Ending workflow.")
            return END
        
        # If we've exceeded max retries, give up
        if retry_count >= 5:
            logger.warning(f"Maximum retries (5) reached. Ending with test failures.")
            return END
        
        # Otherwise, send error feedback back to LLM for fixes
        logger.info(f"Tests failed (attempt {retry_count}/5). Sending errors back to LLM for fixes.")
        return "llm"
    
    # Build the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("llm", llm_node)
    workflow.add_node("tools", tools_node)
    workflow.add_node("human_input", human_input_node)
    workflow.add_node("test", test_node)
    
    # Set entry point
    workflow.set_entry_point("llm")
    
    # Add edges
    workflow.add_conditional_edges(
        "llm",
        should_continue,
        {
            "tools": "tools",
            "human_input": "human_input",
            "test": "test",
            END: END
        }
    )
    workflow.add_conditional_edges(
        "tools",
        should_continue_after_tools,
        {
            "test": "test",
            "llm": "llm"
        }
    )
    workflow.add_edge("human_input", "llm")  # After human responds, go back to LLM
    
    # Add conditional edges from test node
    workflow.add_conditional_edges(
        "test",
        should_continue_after_test,
        {
            "llm": "llm",
            END: END
        }
    )
    
    # Compile the workflow
    return workflow.compile()

