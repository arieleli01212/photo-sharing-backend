# Wedding Photo Sharing Backend

A secure, modular FastAPI backend service for wedding photo sharing with Google OAuth authentication, real-time guest tracking, and image management capabilities.

## 🎯 Features

- **Google OAuth Authentication** - Secure login with Google accounts
- **Image Upload & Management** - Support for JPG, JPEG, PNG files with validation
- **Real-time Guest Tracking** - WebSocket connections for live guest count
- **Secure File Handling** - Content validation, size limits, and unique filename generation
- **Modular Architecture** - Clean separation of concerns with organized directory structure
- **Environment-based Configuration** - Secure credential management
- **CORS Support** - Configurable cross-origin resource sharing
- **Metadata Extraction** - EXIF data extraction from uploaded images

## 🏗️ Architecture

```
├── main.py                          # FastAPI application entry point
├── app/
│   ├── core/
│   │   ├── config.py               # Environment configuration
│   │   └── utils.py                # Helper utilities
│   ├── models/
│   │   └── models.py               # Pydantic data models
│   └── services/
│       ├── auth.py                 # Authentication service
│       └── websocket_manager.py    # WebSocket management
├── uploads/                         # Image storage directory
├── requirements.txt                 # Python dependencies
├── Dockerfile                       # Container configuration
└── .env                            # Environment variables (not in repo)
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Google Cloud Console project with OAuth 2.0 credentials
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/arieleli01212/photo-sharing-backend.git
   cd photo-sharing-backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration (see Environment Configuration section)
   ```

5. **Run the application**
   ```bash
   python main.py
   # Or using uvicorn directly:
   uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```

The API will be available at `http://127.0.0.1:8000`

## ⚙️ Environment Configuration

Create a `.env` file in the project root with the following variables:

```env
# JWT Configuration
SECRET_KEY=your-super-secure-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com

# Server Configuration
SERVER_HOST=127.0.0.1
SERVER_PORT=8000

# File Upload Configuration
UPLOAD_DIR=uploads
MAX_FILE_SIZE=5242880  # 5MB in bytes
```

### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add your domain to authorized origins
6. Copy the Client ID to your `.env` file

## 📡 API Endpoints

### Authentication

#### `POST /google-login`
Authenticate using Google OAuth token.

**Request:**
```json
{
  "token": "google-oauth-token-here"
}
```

**Response:**
```json
{
  "access_token": "jwt-access-token",
  "token_type": "bearer",
  "username": "User Name"
}
```

#### `GET /verify-token`
Verify JWT token validity (requires authentication).

**Headers:**
```
Authorization: Bearer <jwt-token>
```

### File Management

#### `POST /upload`
Upload image files (requires authentication).

**Headers:**
```
Authorization: Bearer <jwt-token>
Content-Type: multipart/form-data
```

**Request:**
- `images`: List of image files (JPG, JPEG, PNG)
- Maximum file size: 5MB per file
- Files are automatically renamed with UUID to prevent conflicts

#### `GET /get-images`
Retrieve list of uploaded images.

**Response:**
```json
[
  "/api/uploads/filename1.jpg",
  "/api/uploads/filename2.png"
]
```

### WebSocket & Guest Tracking

#### `GET /guest`
Get current guest count.

**Response:**
```json
{
  "count": 5
}
```

#### `WebSocket /ws`
Real-time connection for guest count updates.

**Message Format:**
```json
{
  "guestCount": 5
}
```

## 🐳 Docker Deployment

### Build and Run with Docker

```bash
# Build the image
docker build -t wedding-photo-backend .

# Run the container
docker run -p 8000:8000 --env-file .env wedding-photo-backend
```

### Docker Compose (Recommended)

Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  wedding-backend:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./uploads:/app/uploads
    restart: unless-stopped
```

Run with:
```bash
docker-compose up -d
```

## 🔧 Development

### Project Structure

- **`app/core/`** - Core utilities and configuration
- **`app/models/`** - Pydantic data models for request/response
- **`app/services/`** - Business logic services
- **`main.py`** - FastAPI application and route definitions

### Adding New Features

1. **Models**: Add new Pydantic models in `app/models/models.py`
2. **Services**: Create business logic in appropriate service files
3. **Routes**: Add new endpoints in `main.py`
4. **Configuration**: Add new environment variables in `app/core/config.py`

### Code Style

The project follows these conventions:
- Type hints for all functions
- Pydantic models for data validation
- Dependency injection for services
- Environment-based configuration
- Proper error handling with HTTP exceptions

## 🔒 Security Features

- **No Hard-coded Secrets** - All sensitive data in environment variables
- **JWT Token Authentication** - Secure token-based auth
- **File Content Validation** - Verify uploaded files are actually images
- **File Size Limits** - Prevent large file uploads
- **CORS Configuration** - Configurable cross-origin policies
- **Input Sanitization** - Safe filename generation
- **OAuth Integration** - Leverage Google's security infrastructure

## 📊 Monitoring & Logging

- Request/response logging via FastAPI
- WebSocket connection tracking
- File upload success/failure logging
- Authentication attempt logging

## 🚀 Production Deployment

### Environment Considerations

1. **Security:**
   - Use strong, unique `SECRET_KEY`
   - Configure CORS for specific domains only
   - Use HTTPS in production
   - Set up proper firewall rules

2. **Performance:**
   - Use a reverse proxy (nginx)
   - Configure proper caching headers
   - Monitor file storage usage
   - Set up log rotation

3. **Scalability:**
   - Consider using cloud storage for images
   - Implement database for user management
   - Use Redis for session management
   - Set up load balancing if needed

### Example Production Configuration

```env
SECRET_KEY=super-secure-random-key-256-bits
GOOGLE_CLIENT_ID=your-production-client-id.apps.googleusercontent.com
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
UPLOAD_DIR=/var/app/uploads
MAX_FILE_SIZE=10485760  # 10MB for production
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- FastAPI framework for the excellent async web framework
- Google OAuth for secure authentication
- Pillow for image processing capabilities
- All contributors who help improve this project

## 📞 Support

If you encounter any issues or have questions:

1. Check the [Issues](https://github.com/arieleli01212/photo-sharing-backend/issues) page
2. Create a new issue with detailed information
3. Join our discussions for general questions

---

**Built with ❤️ for weddings and special moments**