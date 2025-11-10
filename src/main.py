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
import logfire

from src.containers import Workspace, PlaywrightContainer
from src.tools import FileOperations
from src.llm_client import LLMClient
from src.agent_graph import create_agent_graph
from src.prompts import (
    PIXI_CDN_INSTRUCTIONS, 
    FEEDBACK_CONTEXT_TEMPLATE,
    GAME_DESIGNER_PROMPT,
    GAME_DESIGNER_ASSET_PACK_INFO,
    GAME_DESIGNER_NO_ASSETS,
    GAME_DESIGNER_ASSET_INSTRUCTIONS_WITH_PACK,
    GAME_DESIGNER_ASSET_INSTRUCTIONS_NO_PACK,
    GAME_DESIGNER_SOUND_PACK_INFO,
    GAME_DESIGNER_NO_SOUNDS,
    GAME_DESIGNER_SOUND_INSTRUCTIONS_WITH_PACK,
    GAME_DESIGNER_SOUND_INSTRUCTIONS_NO_PACK
)
from src.session import (
    Session,
    create_session,
    save_session,
    load_session,
    list_sessions,
    get_game_path,
    get_session_path
)
from src.asset_manager import (
    list_available_packs,
    prepare_pack_for_workspace,
    parse_existing_descriptions
)

# Load environment variables
load_dotenv()

# Initialize Logfire for LLM observability (version 4.14.2)
# Configure Logfire - will fail immediately if configuration is invalid
logfire.configure()

# Instrument Anthropic SDK for automatic tracing of all API calls
# This automatically wraps all Anthropic client calls with OpenTelemetry spans
logfire.instrument_anthropic()

print("🔍 Logfire observability enabled (v4.14.2)")
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
        
        # List files that exist on disk before loading
        disk_files = list(context_dir.rglob("*"))
        disk_file_count = len([f for f in disk_files if f.is_file()])
        logger.info(f"Files on disk in {context_dir}: {disk_file_count} files")
        
        # Log sample files (first 10)
        sample_files = [str(f.relative_to(context_dir)) for f in disk_files if f.is_file()][:10]
        if sample_files:
            logger.info(f"Sample files on disk: {sample_files}")
        
        # Load directory from host
        # Use exclude=[] to ensure all files are loaded (don't use default git ignore behavior)
        context = client.host().directory(str(context_dir), exclude=[])
        
        # Verify what Dagger sees in the directory - fail fast if there's an error
        entries = await context.entries()
        logger.info(f"Files loaded by Dagger: {len(entries)} entries")
        logger.info(f"Dagger entries: {entries}")
    
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
    
    # Verify files in workspace after creation
    if context_dir:
        workspace_files = await workspace.ls(".")
        logger.info(f"Files in workspace after creation: {len(workspace_files)} entries")
        logger.info(f"Workspace files: {workspace_files}")
    
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
        
        # Create .gitignore to exclude debug folder
        gitignore_path = game_path / ".gitignore"
        gitignore_path.write_text("debug/\n")
        
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


def create_git_branch(game_path: Path, branch_name: str):
    """Create and checkout a new git branch."""
    logger.info(f"Creating and checking out branch: {branch_name}")
    
    try:
        # Create and checkout new branch
        subprocess.run(["git", "checkout", "-b", branch_name], cwd=game_path, check=True, capture_output=True)
        logger.info(f"Branch created and checked out: {branch_name}")
    except subprocess.CalledProcessError as e:
        # If branch already exists, just check it out
        if "already exists" in e.stderr.decode().lower():
            logger.info(f"Branch {branch_name} already exists, checking it out")
            checkout_git_branch(game_path, branch_name)
        else:
            logger.error(f"Git branch creation error: {e}")
            logger.error(f"Git stderr: {e.stderr.decode() if e.stderr else 'N/A'}")


def checkout_git_branch(game_path: Path, branch_name: str):
    """Switch to an existing git branch."""
    logger.info(f"Checking out branch: {branch_name}")
    
    try:
        subprocess.run(["git", "checkout", branch_name], cwd=game_path, check=True, capture_output=True)
        logger.info(f"Checked out branch: {branch_name}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Git checkout error: {e}")
        logger.error(f"Git stderr: {e.stderr.decode() if e.stderr else 'N/A'}")


def get_current_git_branch(game_path: Path) -> str:
    """Get the current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], 
            cwd=game_path, 
            check=True, 
            capture_output=True,
            text=True
        )
        branch = result.stdout.strip()
        logger.info(f"Current branch: {branch}")
        return branch
    except subprocess.CalledProcessError as e:
        logger.error(f"Git get branch error: {e}")
        logger.error(f"Git stderr: {e.stderr.decode() if e.stderr else 'N/A'}")
        return "master"


def merge_to_master(game_path: Path):
    """Merge current branch to master."""
    logger.info("Merging current branch to master")
    
    try:
        # Get current branch
        current_branch = get_current_git_branch(game_path)
        
        if current_branch == "master":
            logger.info("Already on master, nothing to merge")
            return
        
        # Switch to master
        subprocess.run(["git", "checkout", "master"], cwd=game_path, check=True, capture_output=True)
        
        # Merge the branch
        subprocess.run(["git", "merge", current_branch, "--no-edit"], cwd=game_path, check=True, capture_output=True)
        
        logger.info(f"Merged {current_branch} to master successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Git merge error: {e}")
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
            
            # Skip debug_tests directory (test cases for debugging only)
            if 'debug_tests' in file_path.parts:
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


async def call_game_designer(
    user_prompt: str,
    selected_pack: str | None = None,
    game_path: Path | None = None
) -> str:
    """
    Call game designer LLM to transform user concept into detailed GDD.
    
    Args:
        user_prompt: User's short game concept
        selected_pack: Name of selected asset pack (if any)
        game_path: Path to game directory (where assets are prepared)
    
    Returns:
        Game design document from the LLM
    """
    logger.info("Calling game designer LLM to create GDD")
    print("\n🎨 Game Designer is analyzing your concept...")
    
    # Build asset pack info section
    asset_pack_info = ""
    asset_instructions = ""
    
    if selected_pack and game_path:
        # Get asset list from description.xml
        source_pack_path = Path("assets") / selected_pack
        xml_path = source_pack_path / "description.xml"
        
        if xml_path.exists():
            descriptions = parse_existing_descriptions(xml_path)
            asset_list_lines = []
            
            for filename, info in sorted(descriptions.items()):
                # Get standard attributes
                width = info.get('width', '0')
                height = info.get('height', '0')
                desc = info.get('description', '')
                
                # Start with basic info
                line_parts = [f"- **{filename}** ({width}x{height}px)"]
                
                # Add description if available
                if desc:
                    line_parts.append(f": {desc}")
                
                # Add ALL other custom attributes (not just known ones)
                # This includes human_description and any other custom tags
                custom_attrs = []
                for key, value in sorted(info.items()):
                    # Skip the standard attributes we already handled
                    if key not in ['width', 'height', 'description']:
                        custom_attrs.append(f"{key}: {value}")
                
                # Append custom attributes
                if custom_attrs:
                    if desc:
                        line_parts.append(" | ")
                    else:
                        line_parts.append(": ")
                    line_parts.append(", ".join(custom_attrs))
                
                asset_list_lines.append("".join(line_parts))
            
            asset_list = "\n".join(asset_list_lines)
            asset_pack_info = GAME_DESIGNER_ASSET_PACK_INFO.format(
                pack_name=selected_pack,
                asset_list=asset_list
            )
            asset_instructions = GAME_DESIGNER_ASSET_INSTRUCTIONS_WITH_PACK
        else:
            logger.warning(f"Description XML not found for pack {selected_pack}")
            asset_pack_info = GAME_DESIGNER_NO_ASSETS
            asset_instructions = GAME_DESIGNER_ASSET_INSTRUCTIONS_NO_PACK
    else:
        asset_pack_info = GAME_DESIGNER_NO_ASSETS
        asset_instructions = GAME_DESIGNER_ASSET_INSTRUCTIONS_NO_PACK
    
    # Build sound pack info section
    sound_pack_info = ""
    sound_instructions = ""
    
    if selected_pack and game_path:
        # Get sound list from description.xml
        from src.asset_manager import parse_sound_descriptions
        source_sound_path = Path("Sounds") / selected_pack
        sound_xml_path = source_sound_path / "description.xml"
        
        if sound_xml_path.exists():
            sound_descriptions = parse_sound_descriptions(sound_xml_path)
            sound_list_lines = []
            
            for filename, info in sorted(sound_descriptions.items()):
                # Get attributes
                desc = info.get('description', '')
                sound_type = info.get('type', 'unknown')
                
                # Start with basic info
                line_parts = [f"- **{filename}** (Type: {sound_type})"]
                
                # Add description if available
                if desc:
                    line_parts.append(f": {desc}")
                
                # Add other custom attributes
                custom_attrs = []
                for key, value in sorted(info.items()):
                    if key not in ['description', 'type']:
                        custom_attrs.append(f"{key}: {value}")
                
                # Append custom attributes
                if custom_attrs:
                    if desc:
                        line_parts.append(" | ")
                    else:
                        line_parts.append(": ")
                    line_parts.append(", ".join(custom_attrs))
                
                sound_list_lines.append("".join(line_parts))
            
            sound_list = "\n".join(sound_list_lines)
            sound_pack_info = GAME_DESIGNER_SOUND_PACK_INFO.format(
                pack_name=selected_pack,
                sound_list=sound_list
            )
            sound_instructions = GAME_DESIGNER_SOUND_INSTRUCTIONS_WITH_PACK
        else:
            logger.info(f"No sound description XML found for pack {selected_pack} (optional)")
            sound_pack_info = GAME_DESIGNER_NO_SOUNDS
            sound_instructions = GAME_DESIGNER_SOUND_INSTRUCTIONS_NO_PACK
    else:
        sound_pack_info = GAME_DESIGNER_NO_SOUNDS
        sound_instructions = GAME_DESIGNER_SOUND_INSTRUCTIONS_NO_PACK
    
    # Format the prompt with asset and sound info
    formatted_prompt = GAME_DESIGNER_PROMPT.format(
        asset_pack_info=asset_pack_info,
        asset_instructions=asset_instructions,
        sound_instructions=sound_instructions,
        user_prompt=user_prompt
    )
    
    # Call LLM (no tools needed for game designer)
    llm_client = LLMClient()
    
    with logfire.span(
        "game_designer_llm_call",
        user_prompt=user_prompt[:100],
        has_asset_pack=bool(selected_pack)
    ):
        response = llm_client.call(
            messages=[{"role": "user", "content": user_prompt}],
            tools=[],
            system=formatted_prompt
        )
        
        # Parse response - extract text only
        parsed_content = llm_client.parse_anthropic_response(response)
        
        # Extract text from response
        from src.custom_types import TextRaw
        text_parts = []
        for item in parsed_content:
            if isinstance(item, TextRaw):
                text_parts.append(item.text)
        
        gdd_output = "\n".join(text_parts)
    
    logger.info(f"Game designer produced GDD ({len(gdd_output)} characters)")
    print("✅ Game Design Document created\n")
    
    return gdd_output


async def run_new_game_workflow(client: dagger.Client, task_description: str, selected_pack: str | None = None) -> Session:
    """Run the workflow for creating a new game."""
    logger.info("Starting new game workflow")
    
    # Create session with selected pack
    session = create_session(task_description, selected_pack=selected_pack)
    
    print()
    print(f"📋 Session ID: {session.session_id}")
    print(f"📝 Task: {task_description}")
    if selected_pack:
        print(f"🎨 Asset Pack: {selected_pack}")
    print("=" * 60)
    print()
    
    # Prepare asset pack if selected (before workspace initialization)
    asset_context = None
    sound_context = None
    game_path = get_game_path(session.session_id)
    
    if selected_pack:
        logger.info(f"Preparing asset pack: {selected_pack}")
        print(f"🎨 Preparing asset pack '{selected_pack}'...")
        
        # Prepare assets directory
        assets_dir = game_path / "assets"
        
        # Prepare pack for workspace (generates descriptions and copies files)
        asset_context = prepare_pack_for_workspace(
            pack_name=selected_pack,
            workspace_assets_dir=assets_dir
        )
        
        if asset_context:
            logger.info("Asset pack prepared successfully")
            print("✓ Asset pack ready")
        else:
            logger.warning("Failed to prepare asset pack")
            print("⚠️  Warning: Could not prepare asset pack")
        
        # Prepare sound pack if available (same pack name)
        from src.asset_manager import prepare_sound_pack_for_workspace
        logger.info(f"Checking for sound pack: {selected_pack}")
        print(f"🔊 Checking for sound pack '{selected_pack}'...")
        
        sounds_dir = game_path / "sounds"
        sound_context = prepare_sound_pack_for_workspace(
            pack_name=selected_pack,
            workspace_sounds_dir=sounds_dir
        )
        
        if sound_context:
            logger.info("Sound pack prepared successfully")
            print("✓ Sound pack ready")
        else:
            logger.info("No sound pack found (this is optional)")
            print("ℹ️  No sound pack available")
        print()
    
    # Call game designer LLM to create detailed GDD
    game_designer_output = await call_game_designer(
        user_prompt=task_description,
        selected_pack=selected_pack,
        game_path=game_path if selected_pack else None
    )
    
    # Save GDD to session
    session.game_designer_output = game_designer_output
    save_session(session)
    
    # Also save GDD to file for reference
    gdd_path = get_session_path(session.session_id) / "agent" / "game_design_document.md"
    gdd_path.parent.mkdir(parents=True, exist_ok=True)
    gdd_path.write_text(game_designer_output, encoding='utf-8')
    logger.info(f"Saved GDD to {gdd_path}")
    
    # Print path (already relative if using default base_path="games")
    print(f"📄 Game Design Document saved to: {gdd_path}")
    print()
    
    # Initialize workspace with game path (includes assets if they were prepared)
    workspace = await initialize_workspace(client, context_dir=game_path if selected_pack else None)
    
    # Create Playwright container (reusable for testing)
    playwright_container = await PlaywrightContainer.create(client)
    
    # Initialize components
    llm_client = LLMClient()
    file_ops = FileOperations(workspace=workspace)
    
    # Create agent graph
    agent = create_agent_graph(llm_client, file_ops)
    
    # Initialize state with GDD as the task description
    # NOTE: The game designer output is embedded in this initial prompt but NOT stored
    # in agent message history separately. The agent only sees "implement this GDD"
    # as a single user message. This keeps the agent history clean.
    initial_prompt = f"""TASK:
Implement the following game design:

{game_designer_output}

Please create a complete, working pixi.js game based on this detailed game design document. Make sure to use the correct PixiJS CDN link specified above in your HTML file."""

    initial_state = {
        "messages": [
            HumanMessage(content=initial_prompt)
        ],
        "workspace": workspace,
        "playwright_container": playwright_container,
        "task_description": task_description,
        "is_completed": False,
        "test_failures": [],
        "retry_count": 0,
        "session_id": session.session_id,
        "is_feedback_mode": False,
        "original_prompt": task_description,  # In creation mode, original = current task
        "asset_context": asset_context,  # Asset pack context for prompt injection
        "sound_context": sound_context  # Sound pack context for prompt injection
    }
    
    logger.info("Starting agent execution...")
    print("🤖 Agent is working on your task...\n")
    
    # Initialize final_state for finally block
    final_state = initial_state
    
    try:
        # Set session status
        session.status = "in_progress"
        save_session(session)
        
        # Run the agent
        config = {"recursion_limit": 1000}
        final_state = await agent.ainvoke(initial_state, config=config)
        
        # Check if max retries reached
        if final_state.get("retry_count", 0) >= 5:
            session.status = "max_retries_reached"
            logger.warning("Maximum retries reached")
            print("\n" + "=" * 60)
            print("⚠️  Maximum retry attempts reached")
            print("=" * 60)
            print()
        else:
            session.status = "completed"
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
        
        # Initialize git repo on master first (without files)
        git_folder = game_path / ".git"
        if not git_folder.exists():
            # Create an empty .gitkeep file to initialize repo
            game_path.mkdir(parents=True, exist_ok=True)
            gitkeep_path = game_path / ".gitkeep"
            gitkeep_path.touch()
            init_git_repo(game_path, "Initial commit")
            gitkeep_path.unlink()  # Remove .gitkeep
        
        # Create git branch for this session
        branch_name = f"session/{session.session_id}"
        create_git_branch(game_path, branch_name)
        session.git_branch = branch_name
        
        # Save game files on the branch
        await save_game_files(final_workspace, session, is_new=True)
        
        # If successful, merge to master
        if session.status == "completed":
            merge_to_master(game_path)
            print("✅ Changes merged to master branch")
        
        print(f"✅ Game saved to: {get_game_path(session.session_id)}")
        print(f"✅ To view your game, open {get_game_path(session.session_id)}/index.html in a browser")
        print()
        
        return session
        
    except KeyboardInterrupt:
        session.status = "interrupted"
        session.last_error = "Interrupted by user"
        print("\n\n⚠️  Interrupted by user")
        raise
    except Exception as e:
        session.status = "failed"
        session.last_error = str(e)
        logger.error(f"Error during execution: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        print("Check logs for details.")
        raise
    finally:
        # Always save state (message history and graph state)
        try:
            session.set_message_history(final_state["messages"])
            session.save_graph_state(final_state)
            session.last_modified = datetime.now().isoformat()
            save_session(session)
            logger.info(f"Session state saved: status={session.status}")
            logger.info(f"Saved {len(final_state['messages'])} messages to session history")
        except Exception as e:
            logger.error(f"Failed to save session state: {e}", exc_info=True)


async def run_feedback_workflow(
    client: dagger.Client, 
    session: Session, 
    feedback: str,
    use_message_history: bool = True,
    continue_from_state: bool = False
) -> Session:
    """Run the workflow for providing feedback on an existing game.
    
    Args:
        client: Dagger client
        session: Current session
        feedback: User feedback to apply
        use_message_history: Whether to continue from previous messages (default: True)
        continue_from_state: Whether to restore previous graph state (for recovery) (default: False)
    """
    logger.info(f"Starting feedback workflow for session {session.session_id}")
    logger.info(f"Use message history: {use_message_history}")
    
    game_path = get_game_path(session.session_id)
    
    print()
    print(f"📋 Session ID: {session.session_id}")
    print(f"📝 Original task: {session.initial_prompt}")
    print(f"💬 Feedback: {feedback}")
    if session.selected_pack:
        print(f"🎨 Asset Pack: {session.selected_pack}")
    if not use_message_history:
        print(f"🔄 Starting fresh (not using message history)")
    print("=" * 60)
    print()
    
    # Check and update asset pack if needed
    asset_context = None
    sound_context = None
    if session.selected_pack:
        logger.info(f"Checking asset pack: {session.selected_pack}")
        print(f"🎨 Checking asset pack '{session.selected_pack}'...")
        
        # Prepare assets directory
        assets_dir = game_path / "assets"
        
        # Re-validate and update descriptions if needed
        asset_context = prepare_pack_for_workspace(
            pack_name=session.selected_pack,
            workspace_assets_dir=assets_dir
        )
        
        if asset_context:
            logger.info("Asset pack validated/updated successfully")
            print("✓ Asset pack ready")
        else:
            logger.warning("Failed to validate/update asset pack")
            print("⚠️  Warning: Could not validate asset pack")
        
        # Check for sound pack
        from src.asset_manager import prepare_sound_pack_for_workspace
        logger.info(f"Checking for sound pack: {session.selected_pack}")
        print(f"🔊 Checking for sound pack '{session.selected_pack}'...")
        
        sounds_dir = game_path / "sounds"
        sound_context = prepare_sound_pack_for_workspace(
            pack_name=session.selected_pack,
            workspace_sounds_dir=sounds_dir
        )
        
        if sound_context:
            logger.info("Sound pack validated/updated successfully")
            print("✓ Sound pack ready")
        else:
            logger.info("No sound pack found (this is optional)")
            print("ℹ️  No sound pack available")
        print()
    
    # Build context with existing game files
    project_context = await build_feedback_context(session, game_path)
    
    # Initialize workspace with existing game files
    workspace = await initialize_workspace(client, game_path)
    
    # Create Playwright container (reusable for testing)
    playwright_container = await PlaywrightContainer.create(client)
    
    # Initialize components
    llm_client = LLMClient()
    file_ops = FileOperations(workspace=workspace)
    
    # Create agent graph
    agent = create_agent_graph(llm_client, file_ops)
    
    # Initialize state for feedback mode
    # Optionally load previous message history based on user choice
    if use_message_history:
        previous_messages = session.get_langchain_messages()
        
        if previous_messages:
            logger.info(f"Continuing from {len(previous_messages)} previous messages")
            # Append new feedback message to existing conversation
            feedback_prompt = f"""User Feedback:
{feedback}

Please implement the requested changes. You have access to all the current game files in the workspace."""
            
            messages = previous_messages + [HumanMessage(content=feedback_prompt)]
        else:
            # No message history available, start fresh
            logger.info("No previous message history found, building context from scratch")
            feedback_prompt = FEEDBACK_CONTEXT_TEMPLATE.format(
                project_context=project_context,
                user_prompt=session.initial_prompt,
                feedback=feedback
            )
            messages = [HumanMessage(content=feedback_prompt)]
    else:
        # User chose to start fresh - don't load message history
        logger.info("User chose to start fresh, building context from scratch")
        feedback_prompt = FEEDBACK_CONTEXT_TEMPLATE.format(
            project_context=project_context,
            user_prompt=session.initial_prompt,
            feedback=feedback
        )
        messages = [HumanMessage(content=feedback_prompt)]

    # Initialize state - potentially restore from previous saved state
    if continue_from_state and session.graph_state:
        logger.info("Restoring previous graph state")
        saved_state = session.get_graph_state()
        initial_state = {
            "messages": messages,
            "workspace": workspace,
            "playwright_container": playwright_container,
            "task_description": saved_state.get("task_description", feedback),
            "is_completed": False,  # Reset completion flag to continue
            "test_failures": saved_state.get("test_failures", []),
            "retry_count": saved_state.get("retry_count", 0),
            "session_id": session.session_id,
            "is_feedback_mode": True,
            "original_prompt": saved_state.get("original_prompt", session.initial_prompt),
            "asset_context": asset_context,
            "sound_context": sound_context
        }
        print("🔄 Restoring from previous state...")
        print(f"   Previous retry count: {saved_state.get('retry_count', 0)}")
        print()
    else:
        initial_state = {
            "messages": messages,
            "workspace": workspace,
            "playwright_container": playwright_container,
            "task_description": feedback,
            "is_completed": False,
            "test_failures": [],
            "retry_count": 0,
            "session_id": session.session_id,
            "is_feedback_mode": True,
            "original_prompt": session.initial_prompt,
            "asset_context": asset_context,
            "sound_context": sound_context
        }
    
    logger.info("Starting agent execution in feedback mode...")
    print("🤖 Agent is working on your feedback...\n")
    
    # Initialize final_state for finally block
    final_state = initial_state
    
    try:
        # Checkout or create git branch
        if session.git_branch:
            logger.info(f"Checking out existing branch: {session.git_branch}")
            checkout_git_branch(game_path, session.git_branch)
        else:
            # Create new branch for this feedback iteration
            branch_name = f"session/{session.session_id}"
            create_git_branch(game_path, branch_name)
            session.git_branch = branch_name
        
        # Set session status
        session.status = "in_progress"
        save_session(session)
        
        # Run the agent
        config = {"recursion_limit": 1000}
        final_state = await agent.ainvoke(initial_state, config=config)
        
        # Check if max retries reached
        if final_state.get("retry_count", 0) >= 5:
            session.status = "max_retries_reached"
            logger.warning("Maximum retries reached")
            print("\n" + "=" * 60)
            print("⚠️  Maximum retry attempts reached")
            print("=" * 60)
            print()
        else:
            session.status = "completed"
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
        
        # If successful, merge to master
        if session.status == "completed":
            merge_to_master(game_path)
            print("✅ Changes merged to master branch")
        
        print(f"✅ Game updated in: {get_game_path(session.session_id)}")
        print(f"✅ To view your game, open {get_game_path(session.session_id)}/index.html in a browser")
        print()
        
        return session
        
    except KeyboardInterrupt:
        session.status = "interrupted"
        session.last_error = "Interrupted by user"
        print("\n\n⚠️  Interrupted by user")
        raise
    except Exception as e:
        session.status = "failed"
        session.last_error = str(e)
        logger.error(f"Error during execution: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        print("Check logs for details.")
        raise
    finally:
        # Always save state (message history and graph state)
        try:
            session.set_message_history(final_state["messages"])
            session.save_graph_state(final_state)
            session.last_modified = datetime.now().isoformat()
            save_session(session)
            logger.info(f"Session state saved: status={session.status}")
            logger.info(f"Saved {len(final_state['messages'])} messages to session history")
        except Exception as e:
            logger.error(f"Failed to save session state: {e}", exc_info=True)


async def save_game_files(workspace: Workspace, session: Session, is_new: bool = False, feedback: str | None = None, base_path: Path = Path("games")):
    """Save game files from workspace to session folder."""
    game_path = get_game_path(session.session_id, base_path=base_path)
    session_path = get_session_path(session.session_id, base_path=base_path)
    
    logger.info(f"Saving game files to {game_path}")
    
    # Log what's in workspace before export - fail fast if there's an error
    workspace_files = await workspace.ls(".")
    logger.info(f"Files in workspace before export: {len(workspace_files)} entries")
    logger.info(f"Workspace files: {workspace_files}")
    
    if not is_new:
        # For feedback mode, remove old game files but keep .git and debug
        logger.info("Removing old game files (keeping .git and debug)")
        files_before_cleanup = list(game_path.iterdir())
        logger.info(f"Files before cleanup: {[f.name for f in files_before_cleanup]}")
        
        for item in game_path.iterdir():
            if item.name not in ['.git', 'debug']:
                if item.is_dir():
                    shutil.rmtree(item)
                    logger.info(f"Removed directory: {item.name}")
                else:
                    item.unlink()
                    logger.info(f"Removed file: {item.name}")
        
        files_after_cleanup = list(game_path.iterdir())
        logger.info(f"Files after cleanup: {[f.name for f in files_after_cleanup]}")
    
    # Export workspace to game folder
    logger.info(f"Exporting workspace to {game_path}")
    await workspace.container().directory(".").export(str(game_path))
    logger.info("Export completed")
    
    # Verify files after export
    files_after_export = list(game_path.iterdir())
    logger.info(f"Files after export: {[f.name for f in files_after_export]}")
    all_files = list(game_path.rglob("*"))
    file_count = len([f for f in all_files if f.is_file()])
    logger.info(f"Total files after export: {file_count} files")
    
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
    save_session(session, base_path=base_path)
    
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


def select_asset_pack() -> str | None:
    """Show asset pack selection menu and get user choice."""
    print()
    print("=" * 60)
    print("🎨 Asset Pack Selection")
    print("=" * 60)
    print()
    
    # List available packs
    packs = list_available_packs()
    
    if not packs:
        print("No asset packs found in the 'assets/' directory.")
        print("Continuing without assets...")
        return None
    
    print("Available asset packs:")
    for i, pack_name in enumerate(packs, 1):
        print(f"  {i}. {pack_name}")
    print(f"  0. None (no assets)")
    print()
    
    choice = input("Select pack number (or 0 for none): ").strip()
    
    # Parse choice
    try:
        idx = int(choice)
        if idx == 0:
            print("✓ Continuing without asset pack")
            return None
        elif 1 <= idx <= len(packs):
            selected_pack = packs[idx - 1]
            print(f"✓ Selected pack: {selected_pack}")
            return selected_pack
        else:
            print(f"❌ Invalid selection: {choice}")
            return None
    except ValueError:
        print(f"❌ Invalid input: {choice}")
        return None


def ask_continue_or_fresh(session: Session) -> tuple[bool, bool]:
    """
    Ask user if they want to continue from last state or start fresh.
    
    Args:
        session: Session with potential error/incomplete state
        
    Returns:
        Tuple of (should_proceed, continue_from_state)
        - should_proceed: False if user wants to cancel
        - continue_from_state: True if user wants to restore state
    """
    print()
    print("=" * 60)
    print("⚠️  Session Recovery")
    print("=" * 60)
    print()
    print(f"Session status: {session.status}")
    
    if session.last_error:
        print(f"Last error: {session.last_error}")
    
    if session.graph_state:
        retry_count = session.graph_state.get("retry_count", 0)
        test_failures = session.graph_state.get("test_failures", [])
        print(f"Retry count: {retry_count}/5")
        if test_failures:
            print(f"Test failures: {len(test_failures)}")
    
    print()
    print("What would you like to do?")
    print("  (r) Restore and continue from last state")
    print("  (f) Start fresh feedback iteration")
    print("  (c) Cancel")
    print()
    
    choice = input("Your choice [r/f/c]: ").strip().lower()
    
    if choice == 'r':
        print("✓ Will restore from last state")
        return True, True
    elif choice == 'f':
        print("✓ Will start fresh iteration")
        return True, False
    else:
        print("✓ Cancelled")
        return False, False


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
        status = session.status
        
        # Status emoji
        status_emoji = {
            "completed": "✅",
            "in_progress": "🔄",
            "failed": "❌",
            "max_retries_reached": "⚠️",
            "interrupted": "⏸️"
        }.get(status, "❓")
        
        print(f"{i}. [{session.session_id}]")
        print(f"   Created: {created}")
        print(f"   Prompt: {prompt_preview}")
        print(f"   Iterations: {iterations}")
        print(f"   Status: {status_emoji} {status}")
        if status != "completed" and session.last_error:
            error_preview = session.last_error[:50] + "..." if len(session.last_error) > 50 else session.last_error
            print(f"   Error: {error_preview}")
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
    
    # Note: We create a fresh Dagger connection for each workflow to avoid
    # directory caching issues. Dagger caches host directories by path, which
    # causes stale file data when loading a directory that was modified since
    # the first load. Creating a new client ensures we always see latest files.
    # The performance tradeoff is acceptable for correctness.
    
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
                
                # Select asset pack
                selected_pack = select_asset_pack()
                
                # Create fresh client for this workflow
                async with dagger.Connection() as client:
                    current_session = await run_new_game_workflow(client, task_description, selected_pack)
                
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
                
                # Check session status and handle recovery if needed
                continue_from_state = False
                
                if current_session.status in ["failed", "interrupted", "max_retries_reached", "in_progress"]:
                    # Session needs recovery
                    should_proceed, continue_from_state = ask_continue_or_fresh(current_session)
                    if not should_proceed:
                        current_session = None
                        continue
                
                # Get feedback
                print()
                print(f"Current game: {current_session.initial_prompt[:60]}...")
                print()
                
                # Ask about message history (unless restoring from state)
                use_history = True  # Default
                if not continue_from_state:
                    previous_messages = current_session.get_langchain_messages()
                    if previous_messages:
                        print(f"📝 Found {len(previous_messages)} messages from previous iterations.")
                        print()
                        print("Message history options:")
                        print("  (c) Continue with message history (agent remembers previous conversation)")
                        print("  (f) Start fresh (agent reads files from scratch, no memory of previous iterations)")
                        print()
                        history_choice = input("Your choice [c/f] (default: c): ").strip().lower()
                        
                        if history_choice == 'f':
                            use_history = False
                            print("🔄 Will start fresh without message history")
                        else:
                            print("💬 Will continue with message history")
                        print()
                else:
                    # When restoring from state, always use message history
                    use_history = True
                
                print("What would you like to change or add?")
                print("Example: 'Add a score counter in the top right corner'")
                print()
                feedback = input("Your feedback: ").strip()
                
                if not feedback:
                    print("❌ No feedback provided.")
                    continue
                
                # Create fresh client for this workflow
                async with dagger.Connection() as client:
                    current_session = await run_feedback_workflow(
                        client, 
                        current_session, 
                        feedback,
                        use_message_history=use_history,
                        continue_from_state=continue_from_state
                    )
                
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
