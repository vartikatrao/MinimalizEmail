# MinimalizEmail 🚀

**Transform your inbox from chaos to clarity with AI-powered email intelligence.**

MinimalizEmail is an intelligent email management system that automatically classifies, summarizes, and takes action on your emails. Instead of drowning in endless messages, let AI handle the heavy lifting while you focus on what matters most.


## ✨ Features

### 🤖 **AI-Powered Email Intelligence**
- **Smart Classification**: Automatically categorizes emails as urgent, high-priority or low-priority
- **Instant Summaries**: Get the key points of every email in 1-2 sentences


### ⚡ **Automated Actions**
- **JIRA Integration**: Automatically creates tickets for technical issues and bug reports
- **Calendar Events**: Schedules meetings from email requests with Google Meet links
- **Task Extraction**: Identifies and tracks action items from email content
- **Smart Replies**: Generates contextual draft responses

### 🎯 **Productivity Features**
- **Priority Filtering**: Focus on urgent emails and filter by type (meetings, issues, etc.)
- **Real-time Notifications**: Telegram alerts for truly urgent emails
- **Task Management**: Centralized to-do list extracted from your emails


### 🔧 **Personalization**

- **Custom Criteria**: Define what makes emails urgent or high-priority for you
## 🏗️ Architecture



### Core Components:
- **Backend**: Flask API with SQLAlchemy database
- **AI Pipeline**: LangGraph orchestrating Google Gemini 1.5 Pro
- **Frontend**: React.js with Tailwind CSS
- **Email Processing**: Postmark webhook integration
- **Database**: SQLite for email storage and metadata

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Postmark account
- Google Cloud account (for Gemini API)
- JIRA instance 
- Google Calendar API credentials 
- Telegram bot 

### 1. Clone the Repository
```bash
git clone https://github.com/vartikatrao/minimalize-email.git
cd minimalize-email
```

### 2. Backend Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
```

### 3. Configure Environment Variables
```bash
# .env file
DATABASE_URL=sqlite:///minimalize_email.db
GOOGLE_API_KEY=your_gemini_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
JIRA_DOMAIN=yourcompany.atlassian.net
JIRA_PROJECT_KEY=DEV
JIRA_EMAIL=your_email@company.com
JIRA_API_TOKEN=your_jira_token
```

### 4. Database Setup
```bash
# Initialize database
flask --app app.py init-db
```

### 5. Google Calendar Setup (Optional)
```bash
# Download credentials.json from Google Cloud Console
# Place in project root directory
# First run will open browser for OAuth authentication
```

### 6. Start the Backend
```bash
python app.py
```
Backend will be available at `http://localhost:5000`

### 7. Frontend Setup

Frontend will be available at `http://localhost:3000`

### 8. Configure Postmark Webhook
In your Postmark account:
1. Go to your server's **Webhooks** section
2. Add inbound webhook URL: `http://yourdomain.com/inbound`
3. Enable **Inbound** webhook
4. Set up your inbound email address

## 📋 API Documentation

### Email Endpoints
```http
GET /api/emails                 # Get all emails with optional filtering
GET /api/emails/{id}           # Get specific email details
POST /api/emails/{id}/reply    # Send reply to email
```

### Task Endpoints
```http
GET /api/tasks                 # Get all tasks
POST /api/tasks                # Create new task
POST /api/tasks/{id}/toggle    # Toggle task completion
DELETE /api/tasks/{id}         # Delete task
GET /api/tasks/stats           # Get task statistics
```


### System Endpoints
```http
GET /api/stats                 # Get system statistics
GET /health                    # Health check
POST /inbound                  # Postmark webhook (internal)
```

## 🔧 Configuration

### Email Classification
The system uses your preferences to classify emails. Set up your criteria in the preferences page:

```json
{
  "workSummary": "I'm a software engineer working on web applications",
  "urgentEmails": "Production issues, security alerts, client escalations",
  "highPriorityEmails": "Code reviews, meeting requests, project updates"
}
```

### JIRA Integration
To enable automatic ticket creation:
1. Create an API token in JIRA
2. Set up a project with appropriate permissions
3. Configure environment variables
4. The system will create tickets for emails classified as "issues"

### Google Calendar Integration
To enable meeting scheduling:
1. Enable Google Calendar API in Google Cloud Console
2. Download credentials.json
3. Run the app to complete OAuth flow
4. The system will create events for emails mentioning meetings

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🏆 Postmark Challenge

This project was built for the [Postmark Challenge: Inbox Innovators](https://dev.to/challenges/postmark). It demonstrates innovative use of Postmark's inbound email processing combined with AI to create an intelligent email management system.


## 🔗 Links

- **Live Demo**: [Your deployed app URL]
- **GitHub Repository**: [Your GitHub repo URL]
- **Postmark Challenge**:https://dev.to/challenges/postmark

---

**Built with ❤️ for the Postmark Challenge**