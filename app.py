from flask import Flask, request, render_template, session, redirect, url_for, flash, jsonify, send_file
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timezone
import bcrypt
import os
import re
import uuid
from werkzeug.utils import secure_filename
import mimetypes

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# File upload configuration
UPLOAD_FOLDER = os.path.abspath('uploads')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'mp3', 'wav', 'ogg', 'webm', 'm4a', 'aac', 'flac', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create upload directories and verify permissions
for folder_dir in ['images', 'videos', 'audio', 'documents']:
    folder_path = os.path.join(UPLOAD_FOLDER, folder_dir)
    try:
        os.makedirs(folder_path, exist_ok=True)
        if not os.access(folder_path, os.W_OK):
            raise PermissionError(f"Directory {folder_path} is not writable")
    except Exception as e:
        print(f"Error creating folder {folder_path}: {e}")
        continue

# MongoDB connection
try:
    client = MongoClient('mongodb://localhost:27017/')
    db = client['chat_app']
    users = db['users']
    messages = db['messages']
    conversations = db['conversations']
    # Test connection
    client.admin.command('ping')
    print("Connected to MongoDB successfully!")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")

# Helper functions
def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed):
    """Check if password matches the hashed password"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    return True, "Password is valid"

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename):
    """Determine file type based on extension"""
    if not filename:
        return 'unknown'

    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

    if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']:
        return 'image'
    elif ext in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv']:
        return 'video'
    elif ext in ['mp3', 'wav', 'ogg', 'aac', 'flac', 'm4a', 'webm']:
        return 'audio'
    elif ext in ['pdf', 'doc', 'docx', 'txt', 'rtf']:
        return 'document'
    elif ext in ['xls', 'xlsx', 'csv']:
        return 'spreadsheet'
    elif ext in ['ppt', 'pptx']:
        return 'presentation'
    else:
        return 'file'

def get_file_folder(file_type):
    """Get appropriate folder for file type"""
    if file_type == 'image':
        return 'images'
    elif file_type == 'video':
        return 'videos'
    elif file_type == 'audio':
        return 'audio'
    else:
        return 'documents'

def save_uploaded_file(file):
    """Save uploaded file and return file info"""
    if not file or not allowed_file(file.filename):
        return None

    # Generate unique filename
    original_filename = secure_filename(file.filename)
    file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"

    # Determine file type and folder
    file_type = get_file_type(original_filename)
    folder = get_file_folder(file_type)

    # Create full path
    file_path = os.path.join(UPLOAD_FOLDER, folder, unique_filename)

    try:
        # Save file
        file.save(file_path)

        # Get file size
        file_size = os.path.getsize(file_path)

        return {
            'original_name': original_filename,
            'filename': unique_filename,  # Use just the unique filename
            'file_path': os.path.join(folder, unique_filename),
            'file_type': file_type,
            'file_size': file_size,
            'folder': folder
        }
    except Exception as e:
        print(f"Error saving file: {e}")
        return None

def get_user_conversations(user_id):
    """Get all conversations for a user"""
    try:
        user_conversations = conversations.find({
            'participants': ObjectId(user_id)
        }).sort('last_message_time', -1)

        conversation_list = []
        for conv in user_conversations:
            # Get the other participant
            other_participant_id = None
            for participant_id in conv['participants']:
                if str(participant_id) != user_id:
                    other_participant_id = participant_id
                    break

            if other_participant_id:
                other_user = users.find_one({'_id': other_participant_id})
                if other_user:
                    conversation_list.append({
                        'id': str(conv['_id']),
                        'other_user': {
                            'id': str(other_user['_id']),
                            'name': other_user['name'],
                            'email': other_user['email']
                        },
                        'last_message': conv.get('last_message', ''),
                        'last_message_time': conv.get('last_message_time'),
                        'unread_count': conv.get('unread_count', {}).get(user_id, 0)
                    })

        return conversation_list
    except Exception as e:
        print(f"Error getting conversations: {e}")
        return []

def create_conversation(user1_id, user2_id):
    """Create a new conversation between two users"""
    try:
        # Check if conversation already exists
        existing_conv = conversations.find_one({
            'participants': {'$all': [ObjectId(user1_id), ObjectId(user2_id)]}
        })

        if existing_conv:
            return str(existing_conv['_id'])

        # Create new conversation
        conversation_data = {
            'participants': [ObjectId(user1_id), ObjectId(user2_id)],
            'created_at': datetime.now(timezone.utc),
            'last_message': '',
            'last_message_time': datetime.now(timezone.utc),
            'unread_count': {user1_id: 0, user2_id: 0}
        }

        result = conversations.insert_one(conversation_data)
        return str(result.inserted_id)
    except Exception as e:
        print(f"Error creating conversation: {e}")
        return None

def get_conversation_messages(conversation_id, limit=50):
    """Get messages for a conversation"""
    try:
        conversation_messages = messages.find({
            'conversation_id': ObjectId(conversation_id)
        }).sort('timestamp', 1).limit(limit)

        message_list = []
        for msg in conversation_messages:
            try:
                sender = users.find_one({'_id': msg['sender_id']})
                if not sender:
                    print(f"Warning: Sender not found for message {msg['_id']}")
                    continue

                message_data = {
                    'id': str(msg['_id']),
                    'content': msg['content'],
                    'sender': {
                        'id': str(sender['_id']),
                        'name': sender['name']
                    },
                    'timestamp': msg['timestamp'],
                    'message_type': msg.get('message_type', 'text')
                }

                # Add file information for file messages
                if msg.get('message_type') in ['image', 'video', 'audio', 'file']:
                    message_data.update({
                        'file_name': msg.get('file_name', ''),
                        'file_size': msg.get('file_size', 0),
                        'file_path': msg.get('file_path', ''),
                        'original_name': msg.get('original_name', '')
                    })

                message_list.append(message_data)
            except Exception as msg_error:
                print(f"Error processing message {msg.get('_id', 'unknown')}: {msg_error}")
                continue

        return message_list
    except Exception as e:
        print(f"Error getting messages: {e}")
        return []

def get_conversation_media(conversation_id):
    """Get all media files from a conversation"""
    try:
        media_messages = messages.find({
            'conversation_id': ObjectId(conversation_id),
            'message_type': {'$in': ['image', 'video', 'audio', 'file']}
        }).sort('timestamp', -1)

        media_list = []
        for msg in media_messages:
            try:
                sender = users.find_one({'_id': msg['sender_id']})
                if not sender:
                    print(f"Warning: Sender not found for media message {msg['_id']}")
                    continue

                media_list.append({
                    'id': str(msg['_id']),
                    'file_name': msg.get('file_name', ''),
                    'original_name': msg.get('original_name', ''),
                    'file_size': msg.get('file_size', 0),
                    'file_path': msg.get('file_path', ''),
                    'message_type': msg.get('message_type', 'file'),
                    'timestamp': msg['timestamp'],
                    'sender': {
                        'id': str(sender['_id']),
                        'name': sender['name']
                    }
                })
            except Exception as media_error:
                print(f"Error processing media message {msg.get('_id', 'unknown')}: {media_error}")
                continue

        return media_list
    except Exception as e:
        print(f"Error getting media: {e}")
        return []

# Routes
@app.route('/')
def landing():
    """Landing page"""
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('landing2.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'GET':
        return render_template('register.html')

    # Handle POST request
    try:
        data = request.get_json() if request.is_json else request.form
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        # Validation
        errors = []

        if not name or len(name) < 2:
            errors.append("Name must be at least 2 characters long")

        if not email or not validate_email(email):
            errors.append("Please enter a valid email address")

        is_valid_password, password_message = validate_password(password)
        if not is_valid_password:
            errors.append(password_message)

        if errors:
            if request.is_json:
                return jsonify({'success': False, 'errors': errors}), 400
            else:
                for error in errors:
                    flash(error, 'error')
                return render_template('register.html')

        # Check if user already exists
        existing_user = users.find_one({'email': email})
        if existing_user:
            error_msg = "An account with this email already exists"
            if request.is_json:
                return jsonify({'success': False, 'errors': [error_msg]}), 400
            else:
                flash(error_msg, 'error')
                return render_template('register.html')

        # Create new user
        hashed_password = hash_password(password)
        user_data = {
            'name': name,
            'email': email,
            'password': hashed_password,
            'created_at': datetime.now(timezone.utc),
            'last_login': None,
            'is_active': True
        }

        result = users.insert_one(user_data)

        if result.inserted_id:
            success_msg = "Account created successfully! Please log in."
            if request.is_json:
                return jsonify({'success': True, 'message': success_msg, 'redirect': url_for('login')})
            else:
                flash(success_msg, 'success')
                return redirect(url_for('login'))
        else:
            error_msg = "Failed to create account. Please try again."
            if request.is_json:
                return jsonify({'success': False, 'errors': [error_msg]}), 500
            else:
                flash(error_msg, 'error')
                return render_template('register.html')

    except Exception as e:
        error_msg = "An error occurred during registration. Please try again."
        print(f"Registration error: {e}")
        if request.is_json:
            return jsonify({'success': False, 'errors': [error_msg]}), 500
        else:
            flash(error_msg, 'error')
            return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'GET':
        return render_template('login.html')

    # Handle POST request
    try:
        data = request.get_json() if request.is_json else request.form
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        remember = data.get('remember', False)

        # Validation
        if not email or not password:
            error_msg = "Please enter both email and password"
            if request.is_json:
                return jsonify({'success': False, 'errors': [error_msg]}), 400
            else:
                flash(error_msg, 'error')
                return render_template('login.html')

        # Find user
        user = users.find_one({'email': email})
        if not user or not check_password(password, user['password']):
            error_msg = "Invalid email or password"
            if request.is_json:
                return jsonify({'success': False, 'errors': [error_msg]}), 401
            else:
                flash(error_msg, 'error')
                return render_template('login.html')

        # Check if user is active
        if not user.get('is_active', True):
            error_msg = "Your account has been deactivated. Please contact support."
            if request.is_json:
                return jsonify({'success': False, 'errors': [error_msg]}), 401
            else:
                flash(error_msg, 'error')
                return render_template('login.html')

        # Create session
        session['user_id'] = str(user['_id'])
        session['username'] = user['name']
        session['email'] = user['email']
        session.permanent = remember

        # Update last login
        users.update_one(
            {'_id': user['_id']},
            {'$set': {'last_login': datetime.now(timezone.utc)}}
        )

        success_msg = f"Welcome back, {user['name']}!"
        if request.is_json:
            return jsonify({'success': True, 'message': success_msg, 'redirect': url_for('home')})
        else:
            flash(success_msg, 'success')
            return redirect(url_for('home'))

    except Exception as e:
        error_msg = "An error occurred during login. Please try again."
        print(f"Login error: {e}")
        if request.is_json:
            return jsonify({'success': False, 'errors': [error_msg]}), 500
        else:
            flash(error_msg, 'error')
            return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout"""
    username = session.get('username', 'User')
    session.clear()
    flash(f"Goodbye, {username}! You have been logged out successfully.", 'info')
    return redirect(url_for('landing'))

@app.route('/home')
def home():
    """Home/Dashboard page - requires authentication"""
    if 'user_id' not in session:
        flash('Please log in to access the dashboard.', 'warning')
        return redirect(url_for('login'))

    # Get user's conversations
    user_conversations = get_user_conversations(session['user_id'])

    # Debug: Print conversation data
    print(f"User {session['user_id']} has {len(user_conversations)} conversations:")
    for conv in user_conversations:
        print(f"  - Conversation ID: {conv['id']}, Other user: {conv['other_user']['name']}")

    return render_template('home.html', user=session, conversations=user_conversations)

@app.route('/chat')
def chat():
    """Chat page - requires authentication"""
    if 'user_id' not in session:
        flash('Please log in to access the chat.', 'warning')
        return redirect(url_for('login'))

    conversation_id = request.args.get('id')
    print(f"Chat route called with conversation_id: {conversation_id}")

    if not conversation_id:
        print("No conversation ID provided")
        flash('No conversation selected.', 'warning')
        return redirect(url_for('home'))

    # Get conversation details
    try:
        conversation = conversations.find_one({'_id': ObjectId(conversation_id)})
        if not conversation or ObjectId(session['user_id']) not in conversation['participants']:
            flash('Conversation not found or access denied.', 'error')
            return redirect(url_for('home'))

        # Get the other participant
        other_participant_id = None
        for participant_id in conversation['participants']:
            if str(participant_id) != session['user_id']:
                other_participant_id = participant_id
                break

        other_user = users.find_one({'_id': other_participant_id})
        if not other_user:
            flash('User not found.', 'error')
            return redirect(url_for('home'))

        # Get messages and media
        print(f"Getting messages for conversation {conversation_id}")
        conversation_messages = get_conversation_messages(conversation_id)
        print(f"Found {len(conversation_messages)} messages")

        print(f"Getting media for conversation {conversation_id}")
        conversation_media = get_conversation_media(conversation_id)
        print(f"Found {len(conversation_media)} media files")

        return render_template('chat.html',
                             user=session,
                             conversation_id=conversation_id,
                             other_user=other_user,
                             messages=conversation_messages,
                             shared_media=conversation_media)

    except Exception as e:
        print(f"Error loading chat: {e}")
        flash('Error loading conversation.', 'error')
        return redirect(url_for('home'))

# API Routes
@app.route('/api/send_message', methods=['POST'])
def send_message():
    """Send a message in a conversation"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    try:
        data = request.get_json()
        conversation_id = data.get('conversation_id')
        content = data.get('content', '').strip()

        if not conversation_id or not content:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        # Verify user is part of conversation
        conversation = conversations.find_one({'_id': ObjectId(conversation_id)})
        if not conversation or ObjectId(session['user_id']) not in conversation['participants']:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        # Create message
        message_data = {
            'conversation_id': ObjectId(conversation_id),
            'sender_id': ObjectId(session['user_id']),
            'content': content,
            'timestamp': datetime.now(timezone.utc),
            'message_type': 'text'
        }

        result = messages.insert_one(message_data)

        # Update conversation last message
        conversations.update_one(
            {'_id': ObjectId(conversation_id)},
            {
                '$set': {
                    'last_message': content,
                    'last_message_time': datetime.now(timezone.utc)
                }
            }
        )

        return jsonify({
            'success': True,
            'message': {
                'id': str(result.inserted_id),
                'content': content,
                'sender': {
                    'id': session['user_id'],
                    'name': session['username']
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        })

    except Exception as e:
        print(f"Error sending message: {e}")
        return jsonify({'success': False, 'error': 'Failed to send message'}), 500

@app.route('/api/get_messages/<conversation_id>')
def get_messages(conversation_id):
    """Get messages for a conversation"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    try:
        # Verify user is part of conversation
        conversation = conversations.find_one({'_id': ObjectId(conversation_id)})
        if not conversation or ObjectId(session['user_id']) not in conversation['participants']:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        conversation_messages = get_conversation_messages(conversation_id)
        return jsonify({'success': True, 'messages': conversation_messages})

    except Exception as e:
        print(f"Error getting messages: {e}")
        return jsonify({'success': False, 'error': 'Failed to get messages'}), 500

@app.route('/api/create_conversation', methods=['POST'])
def create_conversation_api():
    """Create a new conversation with another user"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    try:
        data = request.get_json()
        other_user_email = data.get('email', '').strip().lower()

        if not other_user_email:
            return jsonify({'success': False, 'error': 'Email is required'}), 400

        # Find the other user
        other_user = users.find_one({'email': other_user_email})
        if not other_user:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        if str(other_user['_id']) == session['user_id']:
            return jsonify({'success': False, 'error': 'Cannot create conversation with yourself'}), 400

        # Create or get existing conversation
        conversation_id = create_conversation(session['user_id'], str(other_user['_id']))

        if conversation_id:
            return jsonify({
                'success': True,
                'conversation_id': conversation_id,
                'redirect': url_for('chat', id=conversation_id)
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to create conversation'}), 500

    except Exception as e:
        print(f"Error creating conversation: {e}")
        return jsonify({'success': False, 'error': 'Failed to create conversation'}), 500

@app.route('/api/upload_file', methods=['POST'])
def upload_file():
    """Upload a file and send as message"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    try:
        conversation_id = request.form.get('conversation_id')
        if not conversation_id:
            return jsonify({'success': False, 'error': 'Missing conversation ID'}), 400

        # Verify user is part of conversation
        conversation = conversations.find_one({'_id': ObjectId(conversation_id)})
        if not conversation or ObjectId(session['user_id']) not in conversation['participants']:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        # Save file
        file_info = save_uploaded_file(file)
        if not file_info:
            return jsonify({'success': False, 'error': 'Invalid file type or upload failed'}), 400

        # Create message
        message_data = {
            'conversation_id': ObjectId(conversation_id),
            'sender_id': ObjectId(session['user_id']),
            'content': f"Shared {file_info['original_name']}",
            'timestamp': datetime.now(timezone.utc),
            'message_type': file_info['file_type'],
            'file_name': file_info['filename'],
            'original_name': file_info['original_name'],
            'file_size': file_info['file_size'],
            'file_path': file_info['file_path']
        }

        result = messages.insert_one(message_data)

        # Update conversation last message
        conversations.update_one(
            {'_id': ObjectId(conversation_id)},
            {
                '$set': {
                    'last_message': f"📎 {file_info['original_name']}",
                    'last_message_time': datetime.now(timezone.utc)
                }
            }
        )

        return jsonify({
            'success': True,
            'message': {
                'id': str(result.inserted_id),
                'content': message_data['content'],
                'sender': {
                    'id': session['user_id'],
                    'name': session['username']
                },
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'message_type': file_info['file_type'],
                'file_name': file_info['filename'],
                'original_name': file_info['original_name'],
                'file_size': file_info['file_size']
            }
        })

    except Exception as e:
        print(f"Error uploading file: {e}")
        return jsonify({'success': False, 'error': 'Failed to upload file'}), 500

@app.route('/api/upload_voice', methods=['POST'])
def upload_voice():
    """Upload a voice message"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    try:
        conversation_id = request.form.get('conversation_id')
        if not conversation_id:
            return jsonify({'success': False, 'error': 'Missing conversation ID'}), 400

        # Verify user is part of conversation
        conversation = conversations.find_one({'_id': ObjectId(conversation_id)})
        if not conversation or ObjectId(session['user_id']) not in conversation['participants']:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        # Check if voice file was uploaded
        if 'voice' not in request.files:
            return jsonify({'success': False, 'error': 'No voice file uploaded'}), 400

        voice_file = request.files['voice']
        if voice_file.filename == '':
            return jsonify({'success': False, 'error': 'No voice file selected'}), 400

        # Save voice file
        file_info = save_uploaded_file(voice_file)
        if not file_info:
            return jsonify({'success': False, 'error': 'Failed to save voice message'}), 400

        # Create message
        message_data = {
            'conversation_id': ObjectId(conversation_id),
            'sender_id': ObjectId(session['user_id']),
            'content': "🎵 Voice message",
            'timestamp': datetime.now(timezone.utc),
            'message_type': 'audio',
            'file_name': file_info['filename'],
            'original_name': file_info['original_name'],
            'file_size': file_info['file_size'],
            'file_path': file_info['file_path']
        }

        result = messages.insert_one(message_data)

        # Update conversation last message
        conversations.update_one(
            {'_id': ObjectId(conversation_id)},
            {
                '$set': {
                    'last_message': "🎵 Voice message",
                    'last_message_time': datetime.now(timezone.utc)
                }
            }
        )

        return jsonify({
            'success': True,
            'message': {
                'id': str(result.inserted_id),
                'content': message_data['content'],
                'sender': {
                    'id': session['user_id'],
                    'name': session['username']
                },
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'message_type': 'audio',
                'file_name': file_info['filename'],
                'original_name': file_info['original_name'],
                'file_size': file_info['file_size']
            }
        })

    except Exception as e:
        print(f"Error uploading voice: {e}")
        return jsonify({'success': False, 'error': 'Failed to upload voice message'}), 500

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files with proper path handling and download support"""
    try:
        # Construct the full path to search for the file
        for folder in ['images', 'videos', 'audio', 'documents']:
            file_dir = os.path.join(UPLOAD_FOLDER, folder)
            file_path = os.path.join(file_dir, filename)
            
            if os.path.exists(file_path):
                # Get MIME type based on file extension
                content_type, _ = mimetypes.guess_type(file_path)
                
                # Handle PDFs: force download instead of preview
                if filename.lower().endswith('.pdf'):
                    return send_file(
                        file_path,
                        mimetype='application/pdf',
                        as_attachment=True,
                        download_name=filename
                    )
                
                # Return the file with appropriate content type
                return send_file(file_path, mimetype=content_type)

        # If we get here, the file wasn't found
        print(f"File not found: {filename}")
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        print(f"Error serving file: {e}")
        return jsonify({'error': 'Error serving file'}), 500

@app.route('/api/get_media/<conversation_id>')
def get_media(conversation_id):
    """Get media files for a conversation"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    try:
        # Verify user is part of conversation
        conversation = conversations.find_one({'_id': ObjectId(conversation_id)})
        if not conversation or ObjectId(session['user_id']) not in conversation['participants']:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        media_files = get_conversation_media(conversation_id)
        return jsonify({'success': True, 'media': media_files})

    except Exception as e:
        print(f"Error getting media: {e}")
        return jsonify({'success': False, 'error': 'Failed to get media'}), 500

@app.route('/api/delete_message', methods=['POST'])
def delete_message():
    """Delete a message from a conversation"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    try:
        data = request.get_json()
        message_id = data.get('message_id')
        
        if not message_id:
            return jsonify({'success': False, 'error': 'Message ID is required'}), 400

        # Find the message
        message = messages.find_one({'_id': ObjectId(message_id)})
        if not message:
            return jsonify({'success': False, 'error': 'Message not found'}), 404

        # Verify user owns the message
        if str(message['sender_id']) != session['user_id']:
            return jsonify({'success': False, 'error': 'Cannot delete messages from other users'}), 403

        # Delete any associated files if it's a media message
        if message.get('message_type') in ['image', 'video', 'audio', 'file'] and message.get('file_path'):
            try:
                file_path = message['file_path']
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Error deleting file: {e}")

        # Delete the message
        result = messages.delete_one({'_id': ObjectId(message_id)})
        
        if result.deleted_count > 0:
            # Update last message in conversation if this was the last message
            conversation = conversations.find_one({'_id': message['conversation_id']})
            if str(conversation.get('last_message', '')) == str(message.get('content', '')):
                # Get the new last message
                last_message = messages.find_one(
                    {'conversation_id': message['conversation_id']},
                    sort=[('timestamp', -1)]
                )
                
                if last_message:
                    conversations.update_one(
                        {'_id': message['conversation_id']},
                        {
                            '$set': {
                                'last_message': last_message['content'],
                                'last_message_time': last_message['timestamp']
                            }
                        }
                    )
                else:
                    conversations.update_one(
                        {'_id': message['conversation_id']},
                        {
                            '$set': {
                                'last_message': '',
                                'last_message_time': datetime.now(timezone.utc)
                            }
                        }
                    )
                    
            return jsonify({'success': True})
            
        return jsonify({'success': False, 'error': 'Failed to delete message'}), 500

    except Exception as e:
        print(f"Error deleting message: {e}")
        return jsonify({'success': False, 'error': 'Failed to delete message'}), 500

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)