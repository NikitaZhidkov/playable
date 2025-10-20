#!/usr/bin/env python3
"""
Example of programmatic usage of the coding agent.
"""
import asyncio
import dagger
from langchain_core.messages import HumanMessage

from workspace import Workspace
from tools import FileOperations
from llm_client import LLMClient
from agent_graph import create_agent_graph
from log import get_logger
from pixi_cdn import get_pixi_cdn_info

logger = get_logger(__name__)


async def create_simple_game():
    """Example: Create a simple game programmatically."""
    
    task = "Create a simple clicker game where you click a button to increase a score"
    
    logger.info(f"Creating game: {task}")
    
    async with dagger.Connection() as client:
        # Initialize workspace
        workspace = await Workspace.create(
            client=client,
            base_image="oven/bun:1.2.5-alpine",
            setup_cmd=[]
        )
        
        # Initialize components
        llm_client = LLMClient()
        file_ops = FileOperations(workspace=workspace)
        agent = create_agent_graph(llm_client, file_ops)
        
        # Initial state with PixiJS CDN information
        pixi_cdn_info = get_pixi_cdn_info()
        initial_prompt = f"""{pixi_cdn_info}

TASK:
{task}

Please create a complete, working pixi.js game. Make sure to use the correct PixiJS CDN link specified above in your HTML file."""

        state = {
            "messages": [HumanMessage(content=initial_prompt)],
            "workspace": workspace,
            "task_description": task,
            "is_completed": False,
            "test_failures": [],
            "retry_count": 0
        }
        
        # Run agent with increased recursion limit to handle test-fix cycles
        logger.info("Starting agent...")
        config = {"recursion_limit": 100}
        final_state = await agent.ainvoke(state, config=config)
        
        # Get diff
        diff = await workspace.diff()
        logger.info(f"Changes:\n{diff}")
        
        # Export
        output_dir = "./output_game"
        await workspace.container().directory(".").export(output_dir)
        logger.info(f"Game exported to: {output_dir}")
        
        return final_state


if __name__ == "__main__":
    asyncio.run(create_simple_game())

