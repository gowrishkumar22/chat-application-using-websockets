#!/usr/bin/env python3
"""
Script to create test data for the ChatFlow application.
This will create some sample users and conversations for testing.
"""

from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timezone
import bcrypt

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def create_test_data():
    """Create test users and conversations"""
    try:
        # Connect to MongoDB
        client = MongoClient('mongodb://localhost:27017/')
        db = client['chat_app']
        users = db['users']
        conversations = db['conversations']
        messages = db['messages']
        
        print("Creating test data for ChatFlow...")
        
        # Create test users
        test_users = [
            {
                'name': 'Alice Johnson',
                'email': 'alice@example.com',
                'password': hash_password('password123'),
                'created_at': datetime.now(timezone.utc),
                'last_login': None,
                'is_active': True
            },
            {
                'name': 'Bob Smith',
                'email': 'bob@example.com',
                'password': hash_password('password123'),
                'created_at': datetime.now(timezone.utc),
                'last_login': None,
                'is_active': True
            },
            {
                'name': 'Carol Davis',
                'email': 'carol@example.com',
                'password': hash_password('password123'),
                'created_at': datetime.now(timezone.utc),
                'last_login': None,
                'is_active': True
            },
            {
                'name': 'David Wilson',
                'email': 'david@example.com',
                'password': hash_password('password123'),
                'created_at': datetime.now(timezone.utc),
                'last_login': None,
                'is_active': True
            }
        ]
        
        # Insert users (skip if they already exist)
        user_ids = {}
        for user_data in test_users:
            existing_user = users.find_one({'email': user_data['email']})
            if existing_user:
                user_ids[user_data['email']] = existing_user['_id']
                print(f"User {user_data['name']} already exists")
            else:
                result = users.insert_one(user_data)
                user_ids[user_data['email']] = result.inserted_id
                print(f"Created user: {user_data['name']} ({user_data['email']})")
        
        # Create test conversations
        conversation_pairs = [
            ('alice@example.com', 'bob@example.com'),
            ('alice@example.com', 'carol@example.com'),
            ('bob@example.com', 'david@example.com')
        ]
        
        conversation_ids = {}
        for user1_email, user2_email in conversation_pairs:
            user1_id = user_ids[user1_email]
            user2_id = user_ids[user2_email]
            
            # Check if conversation already exists
            existing_conv = conversations.find_one({
                'participants': {'$all': [user1_id, user2_id]}
            })
            
            if existing_conv:
                conversation_ids[(user1_email, user2_email)] = existing_conv['_id']
                print(f"Conversation between {user1_email} and {user2_email} already exists")
            else:
                conversation_data = {
                    'participants': [user1_id, user2_id],
                    'created_at': datetime.now(timezone.utc),
                    'last_message': '',
                    'last_message_time': datetime.now(timezone.utc),
                    'unread_count': {str(user1_id): 0, str(user2_id): 0}
                }
                
                result = conversations.insert_one(conversation_data)
                conversation_ids[(user1_email, user2_email)] = result.inserted_id
                print(f"Created conversation between {user1_email} and {user2_email}")
        
        # Create test messages
        test_messages = [
            # Alice and Bob conversation
            {
                'conversation_id': conversation_ids[('alice@example.com', 'bob@example.com')],
                'sender_id': user_ids['alice@example.com'],
                'content': 'Hey Bob! How are you doing?',
                'timestamp': datetime.now(timezone.utc),
                'message_type': 'text'
            },
            {
                'conversation_id': conversation_ids[('alice@example.com', 'bob@example.com')],
                'sender_id': user_ids['bob@example.com'],
                'content': 'Hi Alice! I\'m doing great, thanks for asking. How about you?',
                'timestamp': datetime.now(timezone.utc),
                'message_type': 'text'
            },
            {
                'conversation_id': conversation_ids[('alice@example.com', 'bob@example.com')],
                'sender_id': user_ids['alice@example.com'],
                'content': 'I\'m good too! Are you ready for the project presentation tomorrow?',
                'timestamp': datetime.now(timezone.utc),
                'message_type': 'text'
            },
            
            # Alice and Carol conversation
            {
                'conversation_id': conversation_ids[('alice@example.com', 'carol@example.com')],
                'sender_id': user_ids['carol@example.com'],
                'content': 'Alice, did you see the new design mockups?',
                'timestamp': datetime.now(timezone.utc),
                'message_type': 'text'
            },
            {
                'conversation_id': conversation_ids[('alice@example.com', 'carol@example.com')],
                'sender_id': user_ids['alice@example.com'],
                'content': 'Yes! They look amazing. Great work on the color scheme.',
                'timestamp': datetime.now(timezone.utc),
                'message_type': 'text'
            },
            
            # Bob and David conversation
            {
                'conversation_id': conversation_ids[('bob@example.com', 'david@example.com')],
                'sender_id': user_ids['david@example.com'],
                'content': 'Bob, can we schedule a code review for this afternoon?',
                'timestamp': datetime.now(timezone.utc),
                'message_type': 'text'
            }
        ]
        
        # Insert messages
        for message_data in test_messages:
            # Check if message already exists (simple check by content and sender)
            existing_message = messages.find_one({
                'conversation_id': message_data['conversation_id'],
                'sender_id': message_data['sender_id'],
                'content': message_data['content']
            })
            
            if not existing_message:
                messages.insert_one(message_data)
                
                # Update conversation last message
                conversations.update_one(
                    {'_id': message_data['conversation_id']},
                    {
                        '$set': {
                            'last_message': message_data['content'],
                            'last_message_time': message_data['timestamp']
                        }
                    }
                )
        
        print("\n✅ Test data created successfully!")
        print("\nTest user credentials (all passwords: 'password123'):")
        for user_data in test_users:
            print(f"  - {user_data['name']}: {user_data['email']}")
        
        print("\n🚀 You can now test the dynamic functionality!")
        print("1. Register a new account or login with test credentials")
        print("2. Start new conversations with test users")
        print("3. Send messages and see real-time updates")
        
    except Exception as e:
        print(f"Error creating test data: {e}")

if __name__ == "__main__":
    create_test_data()
