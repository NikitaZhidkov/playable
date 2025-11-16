from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from src.agent_state import AgentState
from src.llm_client import LLMClient
from src.tools import FileOperations
from src.custom_types import ToolUse, TextRaw, ThinkingBlock
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
    SYSTEM_PIXI_FEEDBACK_PROMPT
)
import logging
import logfire

logger = logging.getLogger(__name__)

# Flag to control whether to use interactive mode (human can respond to LLM questions)
INTERACTIVE_MODE = True


def create_agent_graph(llm_client: LLMClient, file_ops: FileOperations):
    """Create the LangGraph agent workflow."""
    
    async def llm_node(state: AgentState) -> dict:
        """Call the LLM with current state."""
        logger.info("=== LLM Node ===")
        
        # Determine which system prompt to use
        is_feedback = state.get("is_feedback_mode", False)
        retry_count = state.get("retry_count", 0)
        task_description = state.get("task_description", "")
        
        if is_feedback:
            logger.info("Using FEEDBACK mode system prompt")
            system_prompt = SYSTEM_PIXI_FEEDBACK_PROMPT
            mode = "feedback"
        else:
            logger.info("Using CREATION mode system prompt")
            system_prompt = SYSTEM_PIXI_GAME_DEVELOPER_PROMPT
            mode = "creation"
        
        # Note: Asset and sound pack context are now added to user messages, not system prompt
        # This keeps system prompt focused on instructions, user prompt focused on task data
        
        # Get tools from file operations
        tools = file_ops.tools
        
        # Create descriptive span name
        span_name = f"LLM call ({mode})"
        if retry_count > 0:
            span_name += f" - retry {retry_count}"
        
        # Prepare last message for logging (show what we're asking the LLM)
        last_user_message = None
        for msg in reversed(state["messages"]):
            if hasattr(msg, 'type') and msg.type == "human":
                content = msg.content if hasattr(msg, 'content') else str(msg)
                # Truncate very long messages
                if isinstance(content, str) and len(content) > 500:
                    last_user_message = f"{content[:500]}... (length: {len(content)})"
                else:
                    last_user_message = content
                break
        
        # Wrap LLM call with Logfire span for LangGraph context
        with logfire.span(
            span_name,
            langgraph_node="llm",
            mode=mode,
            retry_count=retry_count,
            task_description=task_description[:100] if task_description else "",
            has_asset_context=bool(state.get("asset_context")),
            message_count=len(state["messages"]),
            last_user_message=last_user_message
        ) as span:
            # Call LLM with appropriate system prompt
            response = llm_client.call(
                messages=state["messages"],
                tools=tools,
                system=system_prompt
            )
            
            # Parse response
            parsed_content = llm_client.parse_anthropic_response(response)
            
            # Log LLM response content at top level
            response_summary = []
            for item in parsed_content:
                if isinstance(item, TextRaw):
                    text_preview = item.text[:300] if len(item.text) > 300 else item.text
                    response_summary.append({
                        "type": "text",
                        "content": text_preview + ("..." if len(item.text) > 300 else ""),
                        "full_length": len(item.text)
                    })
                elif isinstance(item, ToolUse):
                    response_summary.append({
                        "type": "tool_use",
                        "name": item.name,
                        "args_keys": list(item.input.keys()) if isinstance(item.input, dict) else []
                    })
                elif isinstance(item, ThinkingBlock):
                    thinking_preview = item.thinking[:200] if len(item.thinking) > 200 else item.thinking
                    response_summary.append({
                        "type": "thinking",
                        "content": thinking_preview + ("..." if len(item.thinking) > 200 else ""),
                        "full_length": len(item.thinking)
                    })
            
            # Add response summary to span
            span.set_attribute("llm_response", response_summary)
        
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
            elif isinstance(item, ThinkingBlock):
                logger.debug(f"Thinking: {item.thinking[:200]}...")
                # Thinking blocks are not included in the message content
        
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
    
    async def tools_node(state: AgentState) -> dict:
        """Execute tool calls."""
        logger.info("=== Tools Node ===")
        
        # Get parsed content from previous node
        parsed_content = state.get("_parsed_content", [])
        
        # Extract tool uses for logging
        tool_uses = [
            item for item in parsed_content 
            if isinstance(item, ToolUse)
        ]
        
        # Create a descriptive span name with the tools being executed
        tool_names = [t.name for t in tool_uses]
        tools_str = ", ".join(tool_names) if tool_names else "no tools"
        span_name = f"Execute tools: {tools_str}"
        
        # Prepare tool details for logging (args and results)
        tool_details = []
        for tool_use in tool_uses:
            # Create a concise representation of tool args
            args_repr = {}
            if isinstance(tool_use.input, dict):
                for key, value in tool_use.input.items():
                    if isinstance(value, str) and len(value) > 100:
                        args_repr[key] = f"{value[:100]}... (length: {len(value)})"
                    else:
                        args_repr[key] = value
            else:
                args_repr = tool_use.input
            
            tool_details.append({
                "name": tool_use.name,
                "args": args_repr
            })
        
        # Wrap tools execution with Logfire span
        with logfire.span(
            span_name,
            langgraph_node="tools",
            tool_count=len(tool_names),
            tools=tool_names,
            tool_details=tool_details,
            is_feedback_mode=state.get("is_feedback_mode", False)
        ) as span:
            # Execute tools
            tool_results, is_completed = await file_ops.run_tools(parsed_content)
            
            # Log tool results in the span
            results_summary = []
            for tool_result in tool_results:
                result_content = tool_result.tool_result.content
                if isinstance(result_content, str) and len(result_content) > 200:
                    result_preview = f"{result_content[:200]}... (length: {len(result_content)})"
                else:
                    result_preview = result_content
                
                results_summary.append({
                    "tool": tool_result.tool_result.name,
                    "result": result_preview,
                    "is_error": tool_result.tool_result.is_error
                })
            
            # Add results to the span attributes
            span.set_attribute("tool_results", results_summary)
            
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
    
    async def build_node(state: AgentState) -> dict:
        """Build TypeScript project as validation step with type checking."""
        logger.info("=== Build Node - TypeScript Type Checking & Compilation ===")
        
        from src.validators.build_validator import validate_build
        
        workspace = state["workspace"]
        retry_count = state.get("retry_count", 0)
        span_name = "Build & type check TypeScript" + (f" - retry {retry_count}" if retry_count > 0 else "")
        
        with logfire.span(
            span_name,
            langgraph_node="build",
            retry_count=retry_count
        ):
            # Call build validator
            result = await validate_build(workspace, retry_count)
        
        # Convert ValidationResult to dict for graph state
        if not result.passed:
            return {
                "messages": [HumanMessage(content=result.error_message)],
                "retry_count": result.retry_count,
                "is_completed": False,  # Reset completion flag
                "test_failures": result.failures
            }
        
        # Build succeeded
        return {
            "messages": [],  # No message needed, proceed to tests
            "retry_count": 0,  # Reset retry count on successful build
            "test_failures": [],  # Clear any previous test failures
            "workspace": result.workspace  # Update workspace with copied files
        }
    
    async def test_node(state: AgentState) -> dict:
        """Test the generated game in a browser and validate with VLM."""
        logger.info("=== Test Node ===")
        
        from src.validators.playable_validator import validate_playable
        
        # Wrap entire test node with Logfire span
        is_feedback_mode = state.get("is_feedback_mode", False)
        retry_count = state.get("retry_count", 0)
        span_name = "Test game with browser" + (f" - retry {retry_count}" if retry_count > 0 else "")
        
        with logfire.span(
            span_name,
            langgraph_node="test",
            is_feedback_mode=is_feedback_mode,
            retry_count=retry_count
        ):
            # Initialize VLM client
            vlm_client = VLMClient()
            
            # Create test run ID for this validation run - all debug files will go here
            from datetime import datetime
            test_run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            logger.info(f"Test run ID: {test_run_id}")
            
            # Validate main playable with VLM
            with logfire.span(
                "VLM: Validate playable",
                validation_type="main_playable",
                is_feedback_mode=is_feedback_mode,
                test_run_id=test_run_id
            ):
                result = await validate_playable(
                    workspace=state["workspace"],
                    playwright_container=state["playwright_container"],
                    vlm_client=vlm_client,
                    task_description=state.get("task_description", ""),
                    session_id=state.get("session_id"),
                    test_run_id=test_run_id,
                    is_feedback_mode=is_feedback_mode,
                    original_prompt=state.get("original_prompt", "") if is_feedback_mode else None,
                    retry_count=retry_count
                )
            
            if not result.passed:
                logger.info(f"Retry attempt {result.retry_count}/5")
                return {
                    "messages": [HumanMessage(content=result.error_message)],
                    "test_failures": result.failures,
                    "retry_count": result.retry_count,
                    "is_completed": False,  # Reset completion flag to retry
                }
            
            # Main VLM validation passed!
            # Check if we previously failed main validation - if so, reset retry count
            previous_failures = state.get("test_failures", [])
            previous_retry_count = state.get("retry_count", 0)
            
            # Reset retry count to 0 since we passed main validation
            if previous_retry_count > 0 and previous_failures:
                logger.info(f"Main VLM validation passed after {previous_retry_count} previous failures - resetting retry count")
            else:
                logger.info("Main VLM validation passed - starting test case validation")
            
            test_case_retry_count = 0
            
            # Run test case validation
            from src.validators.test_case_validator import validate_test_cases
            
            test_case_result = await validate_test_cases(
                workspace=state["workspace"],
                playwright_container=state["playwright_container"],
                vlm_client=vlm_client,
                session_id=state.get("session_id"),
                test_run_id=test_run_id,
                retry_count=test_case_retry_count
            )
            
            if not test_case_result.passed:
                return {
                    "messages": [HumanMessage(content=test_case_result.error_message)],
                    "test_failures": test_case_result.failures,
                    "retry_count": test_case_result.retry_count,
                    "is_completed": False,
                }
            
            # All tests passed!
            logger.info("✅ All test cases passed! Game is fully validated.")
            
            # Move test cases to debug subfolder
            # Note: Keep MANIFEST.json at root for feedback context, only move test_case_*.json
            logger.info("Moving test cases to debug subfolder...")
            try:
                # Discover test case files to move
                test_case_files = await state["workspace"].list_files("test_case_*.json")
                
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
        """Decide whether to go to build or back to LLM after tools execution."""
        # If task is completed and tools succeeded, go to build
        if state.get("is_completed", False):
            logger.info("Task completed successfully, routing to build node")
            return "build"
        
        # Otherwise, continue with LLM
        logger.info("Tools executed, continuing with LLM")
        return "llm"
    
    def should_continue_after_build(state: AgentState) -> str:
        """Decide whether to go to test or back to LLM after build."""
        # Check if there are test failures (build errors are stored here)
        test_failures = state.get("test_failures", [])
        
        if test_failures:
            logger.info("Build failed, routing back to LLM with errors")
            return "llm"
        
        # Build succeeded, proceed to tests
        logger.info("Build successful, routing to test node")
        return "test"
    
    def should_continue_after_test(state: AgentState) -> str:
        """Decide whether to retry after test failures or end."""
        test_failures = state.get("test_failures", [])
        retry_count = state.get("retry_count", 0)
        
        # If no test failures, we're done!
        if not test_failures:
            logger.info("Tests passed! Ending workflow.")
            return END
        
        # If we've exceeded max retries, give up
        if retry_count > 5:
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
    workflow.add_node("build", build_node)
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
            "build": "build",
            "llm": "llm"
        }
    )
    workflow.add_conditional_edges(
        "build",
        should_continue_after_build,
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

