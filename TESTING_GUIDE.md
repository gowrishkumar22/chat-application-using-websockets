# ChatFlow - Dynamic Functionality Testing Guide

## 🚀 Quick Start Testing

### 1. **Test User Accounts**
The system now includes test users with pre-existing conversations:

**Test Credentials (Password: `password123` for all):**
- Alice Johnson: `alice@example.com`
- Bob Smith: `bob@example.com`
- Carol Davis: `carol@example.com`
- David Wilson: `david@example.com`

### 2. **Testing Dynamic Home Page**

#### **Login with Test Account:**
1. Go to `http://localhost:5000`
2. Click "Sign In"
3. Login with: `alice@example.com` / `password123`
4. You should see the dynamic home page with real conversations

#### **Dynamic Features to Test:**
- ✅ **Real Conversations**: See actual conversations with other users
- ✅ **User Avatars**: Dynamic user initials in colored circles
- ✅ **Last Messages**: Real last message content and timestamps
- ✅ **New Chat Modal**: Click "New Chat" to start conversations
- ✅ **User Session**: Your name appears in the header and profile

### 3. **Testing Dynamic Chat Page**

#### **Open Existing Conversation:**
1. From the home page, click on any conversation
2. You'll see the dynamic chat interface with real messages

#### **Send Real Messages:**
1. Type a message in the input field
2. Press Enter or click Send
3. Message appears immediately and is saved to database
4. Switch users and see the conversation from the other perspective

#### **Dynamic Features to Test:**
- ✅ **Real Messages**: Actual message history from database
- ✅ **Message Timestamps**: Real timestamps formatted properly
- ✅ **Sent vs Received**: Different styling for your messages vs others
- ✅ **Auto-scroll**: Automatically scrolls to latest messages
- ✅ **Real-time Sending**: Messages sent via API and saved to MongoDB

### 4. **Testing New Conversation Creation**

#### **Create New Conversation:**
1. From home page, click "New Chat" or "Start New Chat"
2. Enter email of another test user (e.g., `bob@example.com`)
3. Click "Start Chat"
4. You'll be redirected to the new conversation
5. Send messages to test the functionality

## 🧪 Advanced Testing Scenarios

### **Multi-User Testing:**
1. **Open two browser windows/tabs**
2. **Login as different users** in each window:
   - Window 1: `alice@example.com`
   - Window 2: `bob@example.com`
3. **Start a conversation** from Alice's account with Bob
4. **Send messages** from both accounts
5. **Refresh pages** to see persistent message storage

### **Error Handling Testing:**
1. **Try creating conversation with non-existent email**
2. **Try accessing chat without conversation ID**
3. **Try sending empty messages**
4. **Test with invalid conversation IDs**

### **Database Persistence Testing:**
1. **Send several messages**
2. **Restart the Flask application**
3. **Login again** - all messages should still be there
4. **Check MongoDB** directly to see stored data

## 📊 Database Structure

### **Collections Created:**
- `users` - User accounts and authentication
- `conversations` - Chat conversations between users
- `messages` - Individual messages in conversations

### **Sample Data Structure:**

#### **User Document:**
```json
{
  "_id": ObjectId,
  "name": "Alice Johnson",
  "email": "alice@example.com",
  "password": "hashed_password",
  "created_at": "2024-01-01T00:00:00Z",
  "is_active": true
}
```

#### **Conversation Document:**
```json
{
  "_id": ObjectId,
  "participants": [ObjectId("user1"), ObjectId("user2")],
  "last_message": "Hey! How are you?",
  "last_message_time": "2024-01-01T00:00:00Z",
  "unread_count": {"user1_id": 0, "user2_id": 1}
}
```

#### **Message Document:**
```json
{
  "_id": ObjectId,
  "conversation_id": ObjectId,
  "sender_id": ObjectId,
  "content": "Hello there!",
  "timestamp": "2024-01-01T00:00:00Z",
  "message_type": "text"
}
```

## 🔧 API Endpoints

### **Authentication:**
- `POST /register` - User registration
- `POST /login` - User login
- `GET /logout` - User logout

### **Chat Functionality:**
- `GET /home` - Dynamic home page with conversations
- `GET /chat?id=<conversation_id>` - Dynamic chat page
- `POST /api/send_message` - Send a message
- `GET /api/get_messages/<conversation_id>` - Get conversation messages
- `POST /api/create_conversation` - Create new conversation

## 🐛 Troubleshooting

### **Common Issues:**

1. **"No conversations yet" message:**
   - Make sure you've run `python create_test_data.py`
   - Login with test credentials to see pre-created conversations

2. **Messages not sending:**
   - Check browser console for JavaScript errors
   - Ensure MongoDB is running
   - Check Flask terminal for error messages

3. **Conversation not found:**
   - Ensure you're accessing chat with valid conversation ID
   - Check that you're a participant in the conversation

4. **Database connection errors:**
   - Ensure MongoDB is running on `localhost:27017`
   - Check MongoDB service status

### **Reset Test Data:**
If you need to reset the test data:
```bash
# Connect to MongoDB and drop collections
mongo
use chat_app
db.users.drop()
db.conversations.drop()
db.messages.drop()
exit

# Recreate test data
python create_test_data.py
```

## ✅ Success Indicators

Your dynamic functionality is working correctly if you can:

1. ✅ **See real conversations** on the home page after login
2. ✅ **Click on conversations** and see actual message history
3. ✅ **Send messages** that appear immediately and persist after refresh
4. ✅ **Create new conversations** with other users
5. ✅ **See different user perspectives** when switching accounts
6. ✅ **Have messages saved** to MongoDB and persist across sessions

## 🎯 Next Steps

Once basic dynamic functionality is confirmed, consider adding:
- Real-time messaging with WebSocket (Flask-SocketIO)
- File upload and sharing
- Message search functionality
- Group chat support
- Push notifications
- Message encryption
