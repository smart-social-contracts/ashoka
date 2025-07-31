import json
import logging
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class DatabaseClient:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        try:
            self.connection = psycopg2.connect(
                host='localhost',
                database='ashoka_db',
                user='ashoka_user',
                password='ashoka_pass',
                port='5432'
            )
            logger.info("Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    def store_conversation(self, user_principal: str, realm_principal: str, 
                          question: str, response: str, prompt_context: str = None,
                          metadata: Dict = None) -> int:
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO conversations (user_principal, realm_principal, question, response, prompt_context, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (user_principal, realm_principal, question, response, prompt_context, json.dumps(metadata) if metadata else None))
                
                conversation_id = cursor.fetchone()[0]
                self.connection.commit()
                logger.info(f"Stored conversation with ID: {conversation_id}")
                return conversation_id
        except Exception as e:
            logger.error(f"Failed to store conversation: {e}")
            self.connection.rollback()
            raise
    
    def get_conversation(self, conversation_id: int) -> Optional[Dict]:
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM conversations WHERE id = %s", (conversation_id,))
                result = cursor.fetchone()
                if result:
                    result = dict(result)
                    if result['metadata']:
                        result['metadata'] = json.loads(result['metadata'])
                return result
        except Exception as e:
            logger.error(f"Failed to get conversation: {e}")
            return None
    
    def get_conversations_by_user(self, user_principal: str, limit: int = 10) -> List[Dict]:
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM conversations 
                    WHERE user_principal = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """, (user_principal, limit))
                
                results = []
                for row in cursor.fetchall():
                    result = dict(row)
                    if result['metadata']:
                        result['metadata'] = json.loads(result['metadata'])
                    results.append(result)
                return results
        except Exception as e:
            logger.error(f"Failed to get conversations by user: {e}")
            return []
    
    def get_conversation_history(self, user_principal: str, realm_principal: str) -> List[Dict]:
        """Get conversation history for a specific user+realm pair"""
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT question, response FROM conversations 
                    WHERE user_principal = %s AND realm_principal = %s 
                    ORDER BY created_at ASC
                """, (user_principal, realm_principal))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []
    
    def health_check(self) -> bool:
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def close(self):
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
