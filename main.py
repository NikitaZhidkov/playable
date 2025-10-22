#!/usr/bin/env python3
"""
Interactive coding agent for creating pixi.js games with session management.
"""
import asyncio
import logging
import sys
import os
import shutil
import subprocess
from pathlib import Path
from dotenv import load_dotenv            
from datetime import datetime

import dagger
from langchain_core.messages import HumanMessage

from workspace import Workspace
from tools import FileOperations
from llm_client import LLMClient
from agent_graph import create_agent_graph
from playbook import PIXI_CDN_INSTRUCTIONS, FEEDBACK_CONTEXT_TEMPLATE
from session import (
    Session,
    create_session,
    save_session,
    load_session,
    list_sessions,
    get_game_path,
    get_session_path
)

# Load environment variables
load_dotenv()

# Setup LangSmith tracing if API key is available
if not os.getenv("LANGCHAIN_API_KEY") and os.getenv("LANGSMITH_API_KEY"):
    os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY")

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
logger = logging.getLogger(__name__)


async def initialize_workspace(client: dagger.Client, context_dir: Path | None = None) -> Workspace:
    """Initialize a workspace for pixi.js game development."""
    logger.info("Initializing workspace...")
    
    # If context_dir is provided, load existing game files
    context = None
    if context_dir and context_dir.exists():
        logger.info(f"Loading context from: {context_dir}")
        context = client.host().directory(str(context_dir))
    
    # Create workspace with Bun base image
    workspace = await Workspace.create(
        client=client,
        base_image="oven/bun:1.2.5-alpine",
        context=context,
        setup_cmd=[
            ["apk", "add", "--no-cache", "git"]
        ],
        protected=[],  # No protected files for new projects
        allowed=[]  # Allow all files
    )
    
    logger.info("Workspace initialized successfully")
    return workspace


def init_git_repo(game_path: Path, commit_message: str = "Initial commit"):
    """Initialize git repository in the game folder and make initial commit."""
    logger.info(f"Initializing git repo in {game_path}")
    
    try:
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=game_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "agent@appbuild.com"], cwd=game_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Game Agent"], cwd=game_path, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=game_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", commit_message], cwd=game_path, check=True, capture_output=True)
        
        logger.info(f"Git repo initialized with commit: {commit_message}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Git error: {e}")
        logger.error(f"Git stderr: {e.stderr.decode() if e.stderr else 'N/A'}")


def git_commit_changes(game_path: Path, commit_message: str):
    """Commit changes to git repository."""
    logger.info(f"Committing changes to git: {commit_message}")
    
    try:
        subprocess.run(["git", "add", "."], cwd=game_path, check=True, capture_output=True)
        # Check if there are changes to commit
        result = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=game_path, capture_output=True)
        if result.returncode == 0:
            logger.info("No changes to commit")
            return
        
        subprocess.run(["git", "commit", "-m", commit_message], cwd=game_path, check=True, capture_output=True)
        logger.info(f"Changes committed: {commit_message}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Git commit error: {e}")
        logger.error(f"Git stderr: {e.stderr.decode() if e.stderr else 'N/A'}")


async def build_feedback_context(session: Session, game_path: Path) -> str:
    """Build context string with all game files for feedback mode."""
    logger.info(f"Building feedback context for session {session.session_id}")
    
    context_parts = [
        "Current game files:",
        ""
    ]
    
    # Read all files in game directory
    for file_path in sorted(game_path.rglob("*")):
        if file_path.is_file() and not file_path.name.startswith('.'):
            # Skip git files
            if '.git' in file_path.parts:
                continue
            
            rel_path = file_path.relative_to(game_path)
            try:
                content = file_path.read_text(encoding='utf-8')
                context_parts.append(f"=== {rel_path} ===")
                context_parts.append(content)
                context_parts.append("")
            except Exception as e:
                logger.warning(f"Could not read file {rel_path}: {e}")
    
    return "\n".join(context_parts)


async def run_new_game_workflow(client: dagger.Client, task_description: str) -> Session:
    """Run the workflow for creating a new game."""
    logger.info("Starting new game workflow")
    
    # Create session
    session = create_session(task_description)
    
    print()
    print(f"📋 Session ID: {session.session_id}")
    print(f"📝 Task: {task_description}")
    print("=" * 60)
    print()
    
    # Initialize workspace
    workspace = await initialize_workspace(client)
    
    # Initialize components
    llm_client = LLMClient()
    file_ops = FileOperations(workspace=workspace)
    
    # Create agent graph
    agent = create_agent_graph(llm_client, file_ops)
    
    # Initialize state
    initial_prompt = f"""TASK:
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
        "retry_count": 0,
        "session_id": session.session_id,
        "is_feedback_mode": False
    }
    
    logger.info("Starting agent execution...")
    print("🤖 Agent is working on your task...\n")
    
    try:
        # Run the agent
        config = {"recursion_limit": 100}
        final_state = await agent.ainvoke(initial_state, config=config)
        
        print("\n" + "=" * 60)
        print("✅ Task Completed!")
        print("=" * 60)
        print()
        
        # Display test results
        display_test_results(final_state)
        
        # Show diff
        final_workspace = final_state["workspace"]
        diff = await final_workspace.diff()
        if diff:
            print("📝 Changes made:")
            print("-" * 60)
            print(diff)
            print("-" * 60)
        print()
        
        # Save game files
        await save_game_files(final_workspace, session, is_new=True)
        
        print(f"✅ Game saved to: {get_game_path(session.session_id)}")
        print(f"✅ To view your game, open {get_game_path(session.session_id)}/index.html in a browser")
        print()
        
        return session
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        raise
    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        print("Check logs for details.")
        raise


async def run_feedback_workflow(client: dagger.Client, session: Session, feedback: str) -> Session:
    """Run the workflow for providing feedback on an existing game."""
    logger.info(f"Starting feedback workflow for session {session.session_id}")
    
    game_path = get_game_path(session.session_id)
    
    print()
    print(f"📋 Session ID: {session.session_id}")
    print(f"📝 Original task: {session.initial_prompt}")
    print(f"💬 Feedback: {feedback}")
    print("=" * 60)
    print()
    
    # Build context with existing game files
    project_context = await build_feedback_context(session, game_path)
    
    # Initialize workspace with existing game files
    workspace = await initialize_workspace(client, game_path)
    
    # Initialize components
    llm_client = LLMClient()
    file_ops = FileOperations(workspace=workspace)
    
    # Create agent graph
    agent = create_agent_graph(llm_client, file_ops)
    
    # Initialize state for feedback mode
    feedback_prompt = FEEDBACK_CONTEXT_TEMPLATE.format(
        project_context=project_context,
        user_prompt=session.initial_prompt,
        feedback=feedback
    )

    initial_state = {
        "messages": [
            HumanMessage(content=feedback_prompt)
        ],
        "workspace": workspace,
        "task_description": feedback,
        "is_completed": False,
        "test_failures": [],
        "retry_count": 0,
        "session_id": session.session_id,
        "is_feedback_mode": True
    }
    
    logger.info("Starting agent execution in feedback mode...")
    print("🤖 Agent is working on your feedback...\n")
    
    try:
        # Run the agent
        config = {"recursion_limit": 100}
        final_state = await agent.ainvoke(initial_state, config=config)
        
        print("\n" + "=" * 60)
        print("✅ Feedback Applied!")
        print("=" * 60)
        print()
        
        # Display test results
        display_test_results(final_state)
        
        # Show diff
        final_workspace = final_state["workspace"]
        diff = await final_workspace.diff()
        if diff:
            print("📝 Changes made:")
            print("-" * 60)
            print(diff)
            print("-" * 60)
        print()
        
        # Save updated game files
        await save_game_files(final_workspace, session, is_new=False, feedback=feedback)
        
        print(f"✅ Game updated in: {get_game_path(session.session_id)}")
        print(f"✅ To view your game, open {get_game_path(session.session_id)}/index.html in a browser")
        print()
        
        return session
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        raise
    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        print("Check logs for details.")
        raise


async def save_game_files(workspace: Workspace, session: Session, is_new: bool = False, feedback: str | None = None):
    """Save game files from workspace to session folder."""
    game_path = get_game_path(session.session_id)
    session_path = get_session_path(session.session_id)
    
    logger.info(f"Saving game files to {game_path}")
    
    if not is_new:
        # For feedback mode, remove old game files but keep .git
        logger.info("Removing old game files (keeping .git)")
        for item in game_path.iterdir():
            if item.name != '.git':
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
    
    # Export workspace to game folder
    await workspace.container().directory(".").export(str(game_path))
    
    # Initialize or commit to git
    git_folder = game_path / ".git"
    if is_new or not git_folder.exists():
        init_git_repo(game_path, "Initial game creation")
    else:
        commit_msg = f"Feedback iteration: {feedback[:50]}" if feedback else "Game update"
        git_commit_changes(game_path, commit_msg)
    
    # Update session metadata
    timestamp = datetime.now().isoformat()
    if feedback:
        session.add_iteration(feedback, timestamp)
    session.last_modified = timestamp
    save_session(session)
    
    logger.info(f"Game files saved successfully")


def display_test_results(final_state: dict):
    """Display test results from final state."""
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

def show_menu() -> str:
    """Show main menu and get user choice."""
    print()
    print("=" * 60)
    print("🎮 Pixi.js Game Development Agent")
    print("=" * 60)
    print()
    print("What would you like to do?")
    print("  (n) Create a new game")
    print("  (c) Continue working on an existing game")
    print("  (e) Exit")
    print()
    choice = input("Your choice: ").strip().lower()
    return choice


def select_session() -> Session | None:
    """List recent sessions and let user select one."""
    print()
    print("=" * 60)
    print("📚 Recent Sessions")
    print("=" * 60)
    print()
    
    sessions = list_sessions(limit=5)
    
    if not sessions:
        print("No existing sessions found.")
        return None
    
    # Display sessions
    for i, session in enumerate(sessions, 1):
        created = datetime.fromisoformat(session.created_at).strftime("%Y-%m-%d %H:%M")
        prompt_preview = session.initial_prompt[:60] + "..." if len(session.initial_prompt) > 60 else session.initial_prompt
        iterations = len(session.iterations)
        print(f"{i}. [{session.session_id}]")
        print(f"   Created: {created}")
        print(f"   Prompt: {prompt_preview}")
        print(f"   Iterations: {iterations}")
        print()
    
    # Get user selection
    print("Enter session number (1-5) or session ID:")
    selection = input("Selection: ").strip()
    
    # Try to parse as number first
    try:
        idx = int(selection) - 1
        if 0 <= idx < len(sessions):
            return sessions[idx]
    except ValueError:
        pass
    
    # Try as session ID
    session = load_session(selection)
    if session:
        return session
    
    print(f"❌ Invalid selection: {selection}")
    return None


async def main_loop():
    """Main interactive loop."""
    current_session: Session | None = None
    
    while True:
        try:
            choice = show_menu()
            
            if choice == 'e':
                print("\n👋 Goodbye!")
                break
            
            elif choice == 'n':
                # Create new game
                print()
                print("What game would you like to create?")
                print("Example: 'Create a simple platformer game with a character that can jump'")
                print()
                task_description = input("Your task: ").strip()
                
                if not task_description:
                    print("❌ No task provided.")
                    continue
                
                async with dagger.Connection() as client:
                    current_session = await run_new_game_workflow(client, task_description)
                
                # Ask if user wants to continue working
                print()
                continue_work = input("Continue working on this game? (y/n): ").strip().lower()
                if continue_work != 'y':
                    current_session = None
            
            elif choice == 'c':
                # Continue existing game
                if current_session is None:
                    current_session = select_session()
                    if current_session is None:
                        continue
                
                # Get feedback
                print()
                print(f"Current game: {current_session.initial_prompt[:60]}...")
                print()
                print("What would you like to change or add?")
                print("Example: 'Add a score counter in the top right corner'")
                print()
                feedback = input("Your feedback: ").strip()
                
                if not feedback:
                    print("❌ No feedback provided.")
                    continue
                
                async with dagger.Connection() as client:
                    current_session = await run_feedback_workflow(client, current_session, feedback)
                
                # Ask if user wants to continue working
                print()
                continue_work = input("Continue working on this game? (y/n): ").strip().lower()
                if continue_work != 'y':
                    current_session = None
            
            else:
                print(f"❌ Invalid choice: {choice}")
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            print("Returning to menu...")
            continue
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")
            print("Returning to menu...")
            continue


async def main():
    """Main entry point."""
    try:
        await main_loop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
