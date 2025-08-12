#!/usr/bin/env python3
"""
SQLite database for storing journaling conversations and history.
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class Message:
    """Represents a single message in a conversation."""
    id: str
    conversation_id: str
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class Conversation:
    """Represents a conversation session."""
    id: str
    title: str
    user_name: Optional[str]
    current_mood: Optional[str]
    goals: List[str]
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    summary_generated: bool = False

class JournalingDatabase:
    """SQLite database manager for journaling conversations."""
    
    def __init__(self, db_path: str = "journaling.db"):
        """Initialize the database connection and create tables."""
        self.db_path = Path(db_path)
        self.connection = None
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self.connection is None:
            self.connection = sqlite3.connect(
                self.db_path, 
                check_same_thread=False,
                timeout=30.0
            )
            self.connection.row_factory = sqlite3.Row
        return self.connection
    
    def init_database(self):
        """Initialize database tables."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create conversations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                user_name TEXT,
                current_mood TEXT,
                goals TEXT,  -- JSON array of goals
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                summary_generated BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Create messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,  -- JSON metadata
                FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id 
            ON messages (conversation_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
            ON messages (timestamp)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_conversations_updated_at 
            ON conversations (updated_at DESC)
        ''')
        
        # Run migrations
        self._run_migrations()
        
        conn.commit()
        print(f"✅ Database initialized: {self.db_path.absolute()}")
    
    def _run_migrations(self):
        """Run database migrations."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if summary_generated column exists
        cursor.execute("PRAGMA table_info(conversations)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'summary_generated' not in columns:
            print("Running migration: Adding summary_generated column...")
            cursor.execute('''
                ALTER TABLE conversations 
                ADD COLUMN summary_generated BOOLEAN DEFAULT FALSE
            ''')
            print("✅ Migration completed: Added summary_generated column")
    
    def create_conversation(
        self, 
        title: str, 
        user_name: Optional[str] = None,
        current_mood: Optional[str] = None,
        goals: List[str] = None
    ) -> Conversation:
        """Create a new conversation."""
        if goals is None:
            goals = []
        
        conversation_id = str(uuid.uuid4())
        now = datetime.now()
        
        conversation = Conversation(
            id=conversation_id,
            title=title,
            user_name=user_name,
            current_mood=current_mood,
            goals=goals,
            created_at=now,
            updated_at=now
        )
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO conversations (id, title, user_name, current_mood, goals, created_at, updated_at, summary_generated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            conversation.id,
            conversation.title,
            conversation.user_name,
            conversation.current_mood,
            json.dumps(conversation.goals),
            conversation.created_at,
            conversation.updated_at,
            conversation.summary_generated
        ))
        
        conn.commit()
        return conversation
    
    def add_message(
        self, 
        conversation_id: str, 
        role: str, 
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Add a message to a conversation."""
        message_id = str(uuid.uuid4())
        now = datetime.now()
        
        message = Message(
            id=message_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            timestamp=now,
            metadata=metadata
        )
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Insert the message
        cursor.execute('''
            INSERT INTO messages (id, conversation_id, role, content, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            message.id,
            message.conversation_id,
            message.role,
            message.content,
            message.timestamp,
            json.dumps(message.metadata) if message.metadata else None
        ))
        
        # Update conversation's updated_at and message_count
        cursor.execute('''
            UPDATE conversations 
            SET updated_at = ?, message_count = message_count + 1
            WHERE id = ?
        ''', (now, conversation_id))
        
        conn.commit()
        return message
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM conversations WHERE id = ?
        ''', (conversation_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return Conversation(
            id=row['id'],
            title=row['title'],
            user_name=row['user_name'],
            current_mood=row['current_mood'],
            goals=json.loads(row['goals']) if row['goals'] else [],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            message_count=row['message_count'],
            summary_generated=bool(row['summary_generated']) if 'summary_generated' in row.keys() else False
        )
    
    def get_conversations(self, limit: int = 50, offset: int = 0) -> List[Conversation]:
        """Get conversations ordered by most recent."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM conversations 
            ORDER BY updated_at DESC 
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        conversations = []
        for row in cursor.fetchall():
            conversations.append(Conversation(
                id=row['id'],
                title=row['title'],
                user_name=row['user_name'],
                current_mood=row['current_mood'],
                goals=json.loads(row['goals']) if row['goals'] else [],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
                message_count=row['message_count'],
                summary_generated=bool(row['summary_generated']) if 'summary_generated' in row.keys() else False
            ))
        
        return conversations
    
    def get_messages(self, conversation_id: str) -> List[Message]:
        """Get all messages for a conversation."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM messages 
            WHERE conversation_id = ? 
            ORDER BY timestamp ASC
        ''', (conversation_id,))
        
        messages = []
        for row in cursor.fetchall():
            messages.append(Message(
                id=row['id'],
                conversation_id=row['conversation_id'],
                role=row['role'],
                content=row['content'],
                timestamp=datetime.fromisoformat(row['timestamp']),
                metadata=json.loads(row['metadata']) if row['metadata'] else None
            ))
        
        return messages
    
    def update_conversation(
        self, 
        conversation_id: str,
        title: Optional[str] = None,
        current_mood: Optional[str] = None,
        goals: Optional[List[str]] = None
    ) -> bool:
        """Update conversation metadata."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        
        if current_mood is not None:
            updates.append("current_mood = ?")
            params.append(current_mood)
        
        if goals is not None:
            updates.append("goals = ?")
            params.append(json.dumps(goals))
        
        if not updates:
            return False
        
        updates.append("updated_at = ?")
        params.append(datetime.now())
        params.append(conversation_id)
        
        cursor.execute(f'''
            UPDATE conversations 
            SET {', '.join(updates)}
            WHERE id = ?
        ''', params)
        
        conn.commit()
        return cursor.rowcount > 0
    
    def update_conversation_title_and_summary(self, conversation_id: str, title: str) -> bool:
        """Update conversation title and mark as summary generated."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE conversations 
            SET title = ?, summary_generated = ?, updated_at = ?
            WHERE id = ?
        ''', (title, True, datetime.now(), conversation_id))
        
        conn.commit()
        return cursor.rowcount > 0
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM conversations WHERE id = ?', (conversation_id,))
        conn.commit()
        
        return cursor.rowcount > 0
    
    def search_conversations(self, query: str, limit: int = 20) -> List[Conversation]:
        """Search conversations by title or content."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Search in conversation titles and message content
        cursor.execute('''
            SELECT DISTINCT c.* FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            WHERE c.title LIKE ? OR m.content LIKE ?
            ORDER BY c.updated_at DESC
            LIMIT ?
        ''', (f'%{query}%', f'%{query}%', limit))
        
        conversations = []
        for row in cursor.fetchall():
            conversations.append(Conversation(
                id=row['id'],
                title=row['title'],
                user_name=row['user_name'],
                current_mood=row['current_mood'],
                goals=json.loads(row['goals']) if row['goals'] else [],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
                message_count=row['message_count'],
                summary_generated=bool(row['summary_generated']) if 'summary_generated' in row.keys() else False
            ))
        
        return conversations
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as count FROM conversations')
        conversation_count = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM messages')
        message_count = cursor.fetchone()['count']
        
        cursor.execute('''
            SELECT created_at FROM conversations 
            ORDER BY created_at ASC LIMIT 1
        ''')
        first_conversation = cursor.fetchone()
        first_date = first_conversation['created_at'] if first_conversation else None
        
        return {
            'total_conversations': conversation_count,
            'total_messages': message_count,
            'first_conversation_date': first_date,
            'database_size': self.db_path.stat().st_size if self.db_path.exists() else 0
        }
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

# Global database instance
db = JournalingDatabase()