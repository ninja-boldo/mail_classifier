# Mail Classifier

An intelligent email classification service that automatically categorizes incoming emails using AI and moves them to appropriate IMAP folders.

## Features

- **AI-Powered Classification**: Uses Groq AI to intelligently classify emails into custom categories
- **IMAP Integration**: Automatically moves emails to designated folders based on classification
- **Flexible Categories**: Support for custom classification categories (default: important, ad, college, other)
- **RESTful API**: Simple HTTP API for email processing and folder management
- **Docker Support**: Easy deployment with Docker and Docker Compose
- **Secure**: API key authentication for all endpoints

## Prerequisites

- Python 3.11+ (for local development)
- Docker & Docker Compose (for containerized deployment)
- Groq API key ([Get one here](https://console.groq.com/))
- IMAP-enabled email account

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/ninja-boldo/mail_classifier.git
cd mail_classifier
```

### 2. Set Up Environment Variables

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
API_KEY=your-secure-api-key-here
GROQ_API_KEY=your-groq-api-key-here
```

**Important**: Never commit the `.env` file to version control. It's already in `.gitignore`.

### 3. Run with Docker Compose

```bash
docker-compose up --build -d
```

The service will be available at `http://localhost:5000`

### 4. Run Locally (Development)

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the server:

```bash
python server.py
```

## API Endpoints

All endpoints require the `X-API-Key` header with your configured API key.

### Health Check

```bash
GET /health
```

Returns the health status of the service.

### Classify and Move Email

```bash
POST /pipe_mail
Content-Type: application/json
X-API-Key: your-api-key

{
  "host": "imap.example.com",
  "username": "your@email.com",
  "password": "your-password",
  "email_uid": "12345",
  "subject": "Email subject",
  "text": "Email body text",
  "html_text": "Email HTML content",
  "classes": ["important", "ad", "college", "other"]
}
```

### Move Email to Folder

```bash
POST /move-email
Content-Type: application/json
X-API-Key: your-api-key

{
  "host": "imap.example.com",
  "port": 993,
  "username": "your@email.com",
  "password": "your-password",
  "email_uid": "12345",
  "source_folder": "INBOX",
  "target_folder": "Important"
}
```

### List Email Folders

```bash
POST /list-folders
Content-Type: application/json
X-API-Key: your-api-key

{
  "host": "imap.example.com",
  "port": 993,
  "username": "your@email.com",
  "password": "your-password"
}
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `API_KEY` | Yes (Production) | API key for authenticating requests. If not set, runs in unprotected mode (dev only) |
| `GROQ_API_KEY` | Yes | API key for Groq AI service |
| `FLASK_ENV` | No | Flask environment (default: production) |

## Security Best Practices

1. **API Keys**: Always use strong, randomly generated API keys in production
2. **Environment Variables**: Never commit `.env` files or hardcode secrets in code
3. **HTTPS**: Use HTTPS in production to protect credentials in transit
4. **IMAP Credentials**: Use app-specific passwords when available (e.g., Gmail App Passwords)
5. **Docker Images**: Never include `.env` files in Docker images

## Classification

The service uses Groq AI to classify emails based on:
- Email subject
- Email body (plain text and HTML)
- First 1000 characters of content

You can customize classification categories by providing a `classes` array in the request.

## Development

### Project Structure

```
mail_classifier/
├── server.py           # Main Flask application
├── ai_client.py        # AI classification client
├── requirements.txt    # Python dependencies
├── dockerfile          # Docker configuration
├── compose.yaml        # Docker Compose configuration
├── .env.example        # Environment variables template
└── README.md          # This file
```

### Running Tests

```bash
# Add your test commands here
python -m pytest
```

## Troubleshooting

### "API_KEY not set" Warning

This is normal in development mode. Set the `API_KEY` environment variable for production use.

### IMAP Connection Issues

- Verify your IMAP server address and port (usually 993 for SSL)
- Ensure IMAP is enabled on your email account
- Use app-specific passwords for services like Gmail
- Check firewall/network settings

### Docker Port Conflicts

If port 5000 is already in use, modify the port mapping in `compose.yaml`:

```yaml
ports:
  - "8080:3030"  # Use port 8080 instead
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Support

For issues, questions, or contributions, please open an issue on GitHub.
