#!/usr/bin/env python3
"""
Interactive coding agent for creating pixi.js games.
"""
import asyncio
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv            

from datetime import datetime

import dagger
from langchain_core.messages import HumanMessage

from workspace import Workspace
from tools import FileOperations
from llm_client import LLMClient
from agent_graph import create_agent_graph
from log import get_logger
from pixi_cdn import get_pixi_cdn_info

# Load environment variables
load_dotenv()

# Setup LangSmith tracing if API key is available
# Support both LANGCHAIN_API_KEY and LANGSMITH_API_KEY variable names
if not os.getenv("LANGCHAIN_API_KEY") and os.getenv("LANGSMITH_API_KEY"):
    os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY")

# Enable LangSmith tracing if configured
if os.getenv("LANGCHAIN_API_KEY"):
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_PROJECT", "playable-agent")
    print("🔍 LangSmith tracing enabled")
    print(f"   Project: {os.getenv('LANGCHAIN_PROJECT')}")
    print()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = get_logger(__name__)


async def initialize_workspace(client: dagger.Client) -> Workspace:
    """Initialize a workspace for pixi.js game development."""
    logger.info("Initializing workspace...")
    
    # Create workspace with Bun base image
    workspace = await Workspace.create(
        client=client,
        base_image="oven/bun:1.2.5-alpine",
        setup_cmd=[
            ["apk", "add", "--no-cache", "git"]
        ],
        protected=[],  # No protected files for new projects
        allowed=[]  # Allow all files
    )
    
    logger.info("Workspace initialized successfully")
    return workspace


async def run_interactive_agent():
    """Run the interactive coding agent."""
    print("=" * 60)
    print("🎮 Pixi.js Game Development Agent")
    print("=" * 60)
    print()
    print("This agent will help you create pixi.js games from scratch.")
    print("Type your game idea and the agent will build it for you!")
    print()
    
    # Get task from user
    print("What game would you like to create?")
    print("Example: 'Create a simple platformer game with a character that can jump'")
    print()
    task_description = input("Your task: ").strip()
    
    if not task_description:
        print("No task provided. Exiting.")
        return
    
    print()
    print(f"Task: {task_description}")
    print("=" * 60)
    print()
    
    # Initialize Dagger client
    async with dagger.Connection() as client:
        # Initialize workspace
        workspace = await initialize_workspace(client)
        
        # Initialize components
        llm_client = LLMClient()
        file_ops = FileOperations(workspace=workspace)
        
        # Create agent graph
        agent = create_agent_graph(llm_client, file_ops)
        
        # Initialize state with PixiJS CDN information
        pixi_cdn_info = get_pixi_cdn_info()
        initial_prompt = f"""{pixi_cdn_info}

TASK:
{task_description}

Please create a complete, working pixi.js game. Make sure to use the correct PixiJS CDN link specified above in your HTML file."""

        initial_state = {
            "messages": [
                HumanMessage(content=initial_prompt)
            ],
            "workspace": workspace,
            "task_description": task_description,
            "is_completed": False,
            "test_failures": [],
            "retry_count": 0
        }
        
        logger.info("Starting agent execution...")
        print("🤖 Agent is working on your task...\n")
        
        try:
            # Run the agent with increased recursion limit to handle test-fix cycles
            config = {"recursion_limit": 100}
            final_state = await agent.ainvoke(initial_state, config=config)
            
            print("\n" + "=" * 60)
            print("✅ Task Completed!")
            print("=" * 60)
            print()
            
            # Display test results
            test_failures = final_state.get("test_failures", [])
            retry_count = final_state.get("retry_count", 0)
            
            if test_failures:
                print("⚠️  Browser Test Status: FAILED")
                print(f"   Retries: {retry_count}/5")
                print(f"   Errors found:")
                for error in test_failures:
                    print(f"   - {error}")
                print()
            else:
                print("✅ Browser Test Status: PASSED")
                print("   No errors detected in browser")
                print()
            
            # Show diff (use updated workspace from final state)
            logger.info("Generating diff...")
            final_workspace = final_state["workspace"]
            logger.info(f"Got final workspace from state: {type(final_workspace)}")
            diff = await final_workspace.diff()
            
            if diff:
                print("📝 Changes made:")
                print("-" * 60)
                print(diff)
                print("-" * 60)
            else:
                print("No changes were made.")
            
            print()
            
            # Generate automatic export path with game_date_time format
            export_path = datetime.now().strftime("game_%Y%m%d_%H%M%S")
            
            export_path_obj = Path(export_path).resolve()
            export_path_obj.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Exporting to {export_path_obj}")
            await final_workspace.container().directory(".").export(str(export_path_obj))
            print(f"✅ Files exported to: {export_path_obj}")
            print()
            print(f"To view your game, open {export_path_obj}/index.html in a browser")
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
        except Exception as e:
            logger.error(f"Error during execution: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")
            print("Check logs for details.")


async def main():
    """Main entry point."""
    try:
        await run_interactive_agent()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

