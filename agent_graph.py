from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from agent_state import AgentState
from llm_client import LLMClient, VLMClient
from tools import FileOperations
from custom_types import ToolUse, TextRaw
from test_game import validate_game_in_workspace
from utils import validate_playable_with_vlm
from playbook import PLAYABLE_VALIDATION_PROMPT
import logging

logger = logging.getLogger(__name__)

# Flag to control whether to use interactive mode (human can respond to LLM questions)
INTERACTIVE_MODE = True


def create_agent_graph(llm_client: LLMClient, file_ops: FileOperations):
    """Create the LangGraph agent workflow."""
    
    async def llm_node(state: AgentState) -> dict:
        """Call the LLM with current state."""
        logger.info("=== LLM Node ===")
        
        # Get tools from file operations
        tools = file_ops.tools
        
        # Call LLM
        response = llm_client.call(
            messages=state["messages"],
            tools=tools
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
                "messages": [HumanMessage(content="Please continue with the task.")]
            }
    
    async def test_node(state: AgentState) -> dict:
        """Test the generated game in a browser and validate with VLM."""
        logger.info("=== Test Node ===")
        
        try:
            # Initialize VLM client
            vlm_client = VLMClient()

            # Run browser tests to get screenshot and console logs
            logger.info("Running browser tests on generated game...")
            test_result = await validate_game_in_workspace(state["workspace"])
            
            # Check if we have a screenshot for VLM validation
            if not test_result.screenshot_bytes:
                logger.warning("No screenshot available for VLM validation")
                current_retry = state.get("retry_count", 0) + 1
                
                feedback_message = HumanMessage(
                    content=f"Browser test failed to capture screenshot. Please ensure the game generates a valid index.html file. This is attempt {current_retry} of 5."
                )
                
                return {
                    "messages": [feedback_message],
                    "test_failures": ["No screenshot captured"],
                    "retry_count": current_retry,
                    "is_completed": False,
                }
            
            # Validate with VLM
            logger.info("Validating playable with VLM...")
            is_valid, reason = validate_playable_with_vlm(
                vlm_client=vlm_client,
                screenshot_bytes=test_result.screenshot_bytes,
                console_logs=test_result.console_logs,
                user_prompt=state.get("task_description", ""),
                template_str=PLAYABLE_VALIDATION_PROMPT
            )
            
            if is_valid:
                logger.info("✅ VLM validation passed! Game is correct.")
                return {
                    "test_failures": [],
                }
            else:
                logger.warning(f"❌ VLM validation failed: {reason}")
                # Increment retry count
                current_retry = state.get("retry_count", 0) + 1
                logger.info(f"Retry attempt {current_retry}/5")
                
                # Format console logs for feedback
                if test_result.console_logs:
                    console_logs_formatted = "\n".join(test_result.console_logs)
                else:
                    console_logs_formatted = "No console logs captured."
                
                # Create feedback message for LLM as specified in the plan
                feedback_message = HumanMessage(
                    content=f"Playwright validation failed with the reason: {reason}, "
                           f"console_logs: {console_logs_formatted}\n\n"
                           f"Please fix these issues. This is attempt {current_retry} of 5."
                )
                
                return {
                    "messages": [feedback_message],
                    "test_failures": [reason],
                    "retry_count": current_retry,
                    "is_completed": False,  # Reset completion flag to retry
                }
        except Exception as e:
            error_msg = f"Test execution failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            current_retry = state.get("retry_count", 0) + 1
            
            feedback_message = HumanMessage(
                content=f"Browser test execution failed:\n\n- {error_msg}\n\n"
                       f"Please ensure the game generates a valid index.html file. This is attempt {current_retry} of 5."
            )
            
            return {
                "messages": [feedback_message],
                "test_failures": [error_msg],
                "retry_count": current_retry,
                "is_completed": False,
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

