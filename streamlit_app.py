#!/usr/bin/env python3
"""
Streamlit UI for the Journaling Assistant powered by Llama 3.
"""

import streamlit as st
import asyncio
import sys
import os
import nest_asyncio
from datetime import datetime
from typing import List, Dict, Any

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Add the src/journaling_assistant directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'journaling_assistant'))

from sync_agent import SyncJournalingAssistant
from database import db, Conversation, Message
from summarizer import summarizer

# Page configuration
st.set_page_config(
    page_title="🌟 Journaling Assistant",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beautiful styling
st.markdown("""
<style>
    .main {
        padding-top: 2rem;
    }
    
    .stApp > header {
        background-color: transparent;
    }
    
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    
    .user-message {
        background-color: #e3f2fd;
        margin-left: 2rem;
    }
    
    .assistant-message {
        background-color: #f3e5f5;
        margin-right: 2rem;
    }
    
    .mood-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        background-color: #4caf50;
        color: white;
        border-radius: 1rem;
        font-size: 0.875rem;
        margin: 0.25rem;
    }
    
    .goal-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        background-color: #2196f3;
        color: white;
        border-radius: 1rem;
        font-size: 0.875rem;
        margin: 0.25rem;
    }
    
    .welcome-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 1rem;
        margin-bottom: 2rem;
    }
    
    .sidebar-section {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "assistant" not in st.session_state:
        st.session_state.assistant = None
    
    if "user_name" not in st.session_state:
        st.session_state.user_name = ""
    
    if "current_mood" not in st.session_state:
        st.session_state.current_mood = None
    
    if "goals" not in st.session_state:
        st.session_state.goals = []
    
    if "session_started" not in st.session_state:
        st.session_state.session_started = False
    
    # Database-related session state
    if "current_conversation_id" not in st.session_state:
        st.session_state.current_conversation_id = None
    
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    
    if "show_settings" not in st.session_state:
        st.session_state.show_settings = False
    

def run_async(coro):
    """Run async function in streamlit with proper loop handling."""
    try:
        # Since we applied nest_asyncio, we can now run coroutines directly
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    except RuntimeError:
        # Fallback: create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            # Don't close the loop as it might be needed again
            pass

def display_chat_message(message: Dict[str, Any], is_user: bool = False):
    """Display a chat message with proper styling."""
    message_class = "user-message" if is_user else "assistant-message"
    icon = "💭" if is_user else "🤖"
    
    st.markdown(f"""
    <div class="chat-message {message_class}">
        <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
            <span style="font-size: 1.2rem; margin-right: 0.5rem;">{icon}</span>
            <strong>{"You" if is_user else "Assistant"}</strong>
            <span style="margin-left: auto; font-size: 0.8rem; color: #666;">
                {message.get('timestamp', datetime.now().strftime('%H:%M'))}
            </span>
        </div>
        <div>{message['content']}</div>
    </div>
    """, unsafe_allow_html=True)

def save_current_conversation():
    """Save the current conversation to database."""
    if not st.session_state.messages:
        return None
    
    # Create a new conversation if we don't have one
    if not st.session_state.current_conversation_id:
        # Generate title from first user message
        first_message = next((msg for msg in st.session_state.messages if msg["role"] == "user"), None)
        title = first_message["content"][:50] + "..." if first_message and len(first_message["content"]) > 50 else first_message["content"] if first_message else "New Conversation"
        
        conversation = db.create_conversation(
            title=title,
            user_name=st.session_state.user_name or None,
            current_mood=st.session_state.current_mood,
            goals=st.session_state.goals
        )
        st.session_state.current_conversation_id = conversation.id
    
    # Save all messages that aren't already saved
    existing_messages = db.get_messages(st.session_state.current_conversation_id)
    existing_count = len(existing_messages)
    
    # Save new messages
    for i, message in enumerate(st.session_state.messages[existing_count:], start=existing_count):
        db.add_message(
            conversation_id=st.session_state.current_conversation_id,
            role=message["role"],
            content=message["content"],
            metadata={"timestamp_display": message.get("timestamp")}
        )
    
    return st.session_state.current_conversation_id

def load_conversation(conversation_id: str):
    """Load a conversation from database."""
    conversation = db.get_conversation(conversation_id)
    if not conversation:
        st.error("Conversation not found!")
        return
    
    # Load conversation metadata
    st.session_state.current_conversation_id = conversation.id
    st.session_state.user_name = conversation.user_name or ""
    st.session_state.current_mood = conversation.current_mood
    st.session_state.goals = conversation.goals
    
    # Load messages
    messages = db.get_messages(conversation_id)
    st.session_state.messages = []
    
    for msg in messages:
        st.session_state.messages.append({
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp.strftime('%H:%M')
        })
    
    # Reinitialize assistant with loaded context
    if st.session_state.assistant:
        if st.session_state.user_name:
            st.session_state.assistant.context.user_name = st.session_state.user_name
        if st.session_state.current_mood:
            st.session_state.assistant.set_mood(st.session_state.current_mood)
        st.session_state.assistant.context.goals = st.session_state.goals.copy()

def generate_conversation_summary(conversation_id: str):
    """Generate and update conversation summary."""
    try:
        # Get messages for the conversation
        messages = db.get_messages(conversation_id)
        
        if len(messages) >= 2:  # Only summarize if there's actual conversation
            # Generate summary using the summarizer
            summary_title = summarizer.generate_title_sync(messages)
            
            # Update the conversation title in database
            db.update_conversation_title_and_summary(conversation_id, summary_title)
            
            return summary_title
    except Exception as e:
        print(f"Error generating summary: {e}")
        return None

def create_new_conversation():
    """Start a new conversation."""
    st.session_state.current_conversation_id = None
    st.session_state.messages = []

def setup_sidebar():
    """Setup the clean sidebar with quick actions, mood, and history."""
    with st.sidebar:
        # Quick Actions
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown("### ⚡ Quick Actions")
        
        if st.button("📝 New Chat", use_container_width=True):
            create_new_conversation()
            st.rerun()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💭 Daily Reflection", help="Reflect on your day"):
                st.session_state.messages.append({
                    "role": "user",
                    "content": "Help me reflect on my day. What went well and what could I improve?",
                    "timestamp": datetime.now().strftime('%H:%M')
                })
                st.rerun()
        
        with col2:
            if st.button("🌱 Gratitude Practice", help="Practice gratitude"):
                st.session_state.messages.append({
                    "role": "user",
                    "content": "Let's practice gratitude. Help me identify things I'm grateful for today.",
                    "timestamp": datetime.now().strftime('%H:%M')
                })
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Mood section
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown("### 😊 Current Mood")
        
        mood_options = [
            "Happy", "Sad", "Anxious", "Excited", "Calm", "Frustrated", 
            "Grateful", "Confused", "Energetic", "Tired", "Hopeful", "Overwhelmed"
        ]
        
        # Handle case where stored mood isn't in predefined options
        current_mood_index = 0  # Default to "Not set"
        if st.session_state.current_mood:
            try:
                current_mood_index = mood_options.index(st.session_state.current_mood) + 1
            except ValueError:
                # If stored mood isn't in options, add it temporarily or default to "Not set"
                if st.session_state.current_mood not in mood_options:
                    mood_options_with_current = mood_options + [st.session_state.current_mood]
                    current_mood_index = len(mood_options)  # Index of the added mood
                else:
                    current_mood_index = 0
        
        # Use extended options if we have a custom mood
        display_options = ["Not set"] + mood_options
        if (st.session_state.current_mood and 
            st.session_state.current_mood not in mood_options):
            display_options.append(st.session_state.current_mood)
            current_mood_index = len(display_options) - 1
        
        selected_mood = st.selectbox(
            "How are you feeling?",
            options=display_options,
            index=current_mood_index
        )
        
        if selected_mood != "Not set" and selected_mood != st.session_state.current_mood:
            st.session_state.current_mood = selected_mood
            if st.session_state.assistant:
                st.session_state.assistant.set_mood(selected_mood)
            st.success(f"Mood set to: {selected_mood}")
        
        if st.session_state.current_mood:
            st.markdown(f'<span class="mood-badge">😊 {st.session_state.current_mood}</span>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Conversation History
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown("### 📚 Conversation History")
        
        # Always show conversation history
        conversations = db.get_conversations(limit=8)
        
        if conversations:
            for conv in conversations:
                # Create a button for each conversation
                conv_preview = conv.title[:25] + "..." if len(conv.title) > 25 else conv.title
                
                # Add icon based on summary status
                if not conv.summary_generated and conv.message_count >= 2:
                    button_text = f"🔄 {conv_preview}"  # Needs summary
                else:
                    button_text = f"💬 {conv_preview}"  # Has summary or too short
                
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    if st.button(button_text, key=f"load_{conv.id}"):
                        load_conversation(conv.id)
                        st.rerun()
                
                with col2:
                    # Show summarize button for conversations that need it
                    if not conv.summary_generated and conv.message_count >= 2:
                        if st.button("📝", key=f"summarize_{conv.id}", help="Generate summary"):
                            with st.spinner("Generating summary..."):
                                summary_title = generate_conversation_summary(conv.id)
                                if summary_title:
                                    st.success("Summary generated!")
                                else:
                                    st.error("Failed to generate summary")
                            st.rerun()
                
                with col3:
                    if st.button("🗑️", key=f"delete_{conv.id}"):
                        db.delete_conversation(conv.id)
                        st.success("Conversation deleted!")
                        st.rerun()
                
                # Show conversation info
                st.caption(f"📅 {conv.updated_at.strftime('%m/%d %H:%M')} • {conv.message_count} msgs")
        else:
            st.info("No conversations yet. Start chatting!")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Settings at bottom
        st.markdown("---")
        if st.button("⚙️ Settings", use_container_width=True):
            st.session_state.show_settings = True
            st.rerun()

def setup_settings_tab():
    """Setup the settings interface."""
    # Back button at the top
    if st.button("← Back to Journal", use_container_width=True):
        st.session_state.show_settings = False
        st.rerun()
    
    st.markdown("## ⚙️ Settings")
    
    # User Profile Section
    st.markdown("### 👤 User Profile")
    with st.container():
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # User name input
            user_name = st.text_input(
                "Your name",
                value=st.session_state.user_name,
                placeholder="Enter your name...",
                help="This helps personalize your journaling experience"
            )
            
            if user_name != st.session_state.user_name:
                st.session_state.user_name = user_name
                if st.session_state.assistant:
                    st.session_state.assistant.context.user_name = user_name or None
                st.success("Profile updated!")
        
        with col2:
            if st.session_state.user_name:
                st.info(f"👋 Hello, {st.session_state.user_name}")
            else:
                st.info("👋 Hello, Anonymous")
    
    st.markdown("---")
    
    # Goals Management Section
    st.markdown("### 🎯 Goals Management")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        new_goal = st.text_input("Add a new goal:", placeholder="e.g., Practice mindfulness daily")
    
    with col2:
        if st.button("Add Goal", disabled=not new_goal.strip()):
            if st.session_state.assistant:
                st.session_state.assistant.add_goal(new_goal.strip())
            st.session_state.goals.append(new_goal.strip())
            st.success(f"Goal added: {new_goal}")
            st.rerun()
    
    # Display current goals
    if st.session_state.goals:
        st.markdown("**Your Current Goals:**")
        for i, goal in enumerate(st.session_state.goals):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"• {goal}")
            with col2:
                if st.button("Remove", key=f"remove_goal_settings_{i}"):
                    st.session_state.goals.pop(i)
                    if st.session_state.assistant:
                        st.session_state.assistant.context.goals = st.session_state.goals.copy()
                    st.success("Goal removed!")
                    st.rerun()
    else:
        st.info("No goals set yet. Add some goals to track your progress!")
    
    st.markdown("---")
    
    # Import/Export Section
    st.markdown("### 📁 Import / Export")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📤 Export Data")
        
        # Export current conversation
        if st.button("📄 Export Current Conversation", disabled=not st.session_state.messages):
            export_text = f"# Journal Session - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            if st.session_state.user_name:
                export_text += f"**User:** {st.session_state.user_name}\n"
            if st.session_state.current_mood:
                export_text += f"**Mood:** {st.session_state.current_mood}\n"
            if st.session_state.goals:
                export_text += f"**Goals:** {', '.join(st.session_state.goals)}\n"
            export_text += "\n---\n\n"
            
            for msg in st.session_state.messages:
                role = "You" if msg["role"] == "user" else "Assistant"
                export_text += f"**{role}:** {msg['content']}\n\n"
            
            st.download_button(
                label="Download Current Session",
                data=export_text,
                file_name=f"journal_session_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                mime="text/markdown"
            )
        
        # Export all conversations
        if st.button("📚 Export All Conversations"):
            conversations = db.get_conversations(limit=1000)  # Get all conversations
            
            export_text = f"# Complete Journal Export - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            export_text += f"Total Conversations: {len(conversations)}\n\n"
            
            for conv in conversations:
                export_text += f"## {conv.title}\n"
                export_text += f"**Date:** {conv.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                if conv.user_name:
                    export_text += f"**User:** {conv.user_name}\n"
                if conv.current_mood:
                    export_text += f"**Mood:** {conv.current_mood}\n"
                if conv.goals:
                    export_text += f"**Goals:** {', '.join(conv.goals)}\n"
                export_text += "\n---\n\n"
                
                messages = db.get_messages(conv.id)
                for msg in messages:
                    role = "You" if msg.role == "user" else "Assistant"
                    export_text += f"**{role}:** {msg.content}\n\n"
                
                export_text += "\n" + "="*50 + "\n\n"
            
            st.download_button(
                label="Download Complete Journal",
                data=export_text,
                file_name=f"complete_journal_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                mime="text/markdown"
            )
    
    with col2:
        st.markdown("#### 📥 Import Data")
        st.info("Import functionality coming soon! Currently supports manual conversation loading.")
    
    st.markdown("---")
    
    # Database Statistics
    st.markdown("### 📊 Statistics")
    stats = db.get_stats()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Conversations", stats['total_conversations'])
    with col2:
        st.metric("Total Messages", stats['total_messages'])
    with col3:
        db_size_mb = stats['database_size'] / (1024 * 1024) if stats['database_size'] > 0 else 0
        st.metric("Database Size", f"{db_size_mb:.2f} MB")
    
    if stats['first_conversation_date']:
        st.info(f"📅 First conversation: {stats['first_conversation_date']}")
    
    st.markdown("---")

def main():
    """Main Streamlit app."""
    initialize_session_state()
    
    # Always setup sidebar (for navigation)
    setup_sidebar()
    
    # Check if we should show settings
    if st.session_state.show_settings:
        setup_settings_tab()
        return
    
    # Header
    st.markdown("""
    <div class="welcome-header">
        <h1>🌟 AI Journaling Assistant</h1>
        <p>Your personal companion for reflection, growth, and self-discovery</p>
        <p><em>Powered by Llama 3 via Ollama</em></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize assistant if not done
    if not st.session_state.session_started:
        with st.spinner("Initializing your journaling assistant..."):
            try:
                st.session_state.assistant = SyncJournalingAssistant(
                    user_name=st.session_state.user_name or None
                )
                
                # Set initial mood and goals if they exist
                if st.session_state.current_mood:
                    st.session_state.assistant.set_mood(st.session_state.current_mood)
                
                for goal in st.session_state.goals:
                    st.session_state.assistant.add_goal(goal)
                
                st.session_state.session_started = True
            except Exception as e:
                st.error(f"❌ Error initializing assistant: {str(e)}")
                st.info("💡 Make sure Ollama is running with the llama3:latest model.")
                st.stop()
    
    # Chat interface
    st.markdown("### 💬 Journal Conversation")
    
    # Create a container for the chat messages with fixed height
    chat_container = st.container()
    
    # Display chat history
    if st.session_state.messages:
        with chat_container:
            for message in st.session_state.messages:
                display_chat_message(message, is_user=(message["role"] == "user"))
    else:
        with chat_container:
            st.info("👋 Welcome! Start by sharing your thoughts or feelings. I'm here to listen and help you reflect.")
    
    # Chat input at the bottom
    user_input = st.chat_input("Share your thoughts, feelings, or ask for guidance...")
    
    if user_input:
        # Add user message
        user_message = {
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().strftime('%H:%M')
        }
        st.session_state.messages.append(user_message)
        
        # Auto-save user message
        try:
            if not st.session_state.current_conversation_id:
                # Create new conversation
                title = user_input[:50] + "..." if len(user_input) > 50 else user_input
                conversation = db.create_conversation(
                    title=title,
                    user_name=st.session_state.user_name or None,
                    current_mood=st.session_state.current_mood,
                    goals=st.session_state.goals
                )
                st.session_state.current_conversation_id = conversation.id
            
            # Save user message
            db.add_message(
                conversation_id=st.session_state.current_conversation_id,
                role="user",
                content=user_input,
                metadata={"timestamp_display": user_message["timestamp"]}
            )
        except Exception as e:
            st.error(f"Failed to save message: {str(e)}")
        
        # Get assistant response
        with st.spinner("🤖 Assistant is thinking..."):
            try:
                # Now we can call it synchronously
                response = st.session_state.assistant.chat(user_input, stream=False)
                
                assistant_message = {
                    "role": "assistant", 
                    "content": response,
                    "timestamp": datetime.now().strftime('%H:%M')
                }
                st.session_state.messages.append(assistant_message)
                
                # Auto-save assistant message
                try:
                    db.add_message(
                        conversation_id=st.session_state.current_conversation_id,
                        role="assistant",
                        content=response,
                        metadata={"timestamp_display": assistant_message["timestamp"]}
                    )
                    
                    # Auto-generate summary if conversation is long enough and doesn't have one
                    conversation = db.get_conversation(st.session_state.current_conversation_id)
                    if (conversation and conversation.message_count >= 4 and 
                        not conversation.summary_generated):
                        # Generate summary in the background
                        try:
                            generate_conversation_summary(st.session_state.current_conversation_id)
                        except Exception as e:
                            print(f"Background summary generation failed: {e}")
                    
                except Exception as e:
                    st.error(f"Failed to save assistant response: {str(e)}")
                
            except Exception as e:
                st.error(f"❌ Error getting response: {str(e)}")
                st.info("💡 Make sure Ollama is running with the llama3:latest model")
        
        # Rerun to update the display
        st.rerun()
    

if __name__ == "__main__":
    main()