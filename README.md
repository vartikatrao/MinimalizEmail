# MinimalizEmail 🚀
![image](https://github.com/user-attachments/assets/0d752a28-8b47-4fb9-b10a-94162bb31aba)

**Transform your inbox from chaos to clarity with AI-powered email intelligence.**


## ✨ Features

### 🤖 **AI-Powered Email Intelligence**

* **Smart Classification**: Automatically categorizes emails as urgent, high-priority or low-priority
* **Instant Summaries**: Get the key points of every email in 1-2 sentences

### ⚡ **Automated Actions**

* **JIRA Integration**: Automatically creates tickets for technical issues and bug reports
* **Calendar Events**: Schedules meetings from email requests with Google Meet links
* **Task Extraction**: Identifies and tracks action items from email content
* **Smart Replies**: Generates contextual draft responses

### 🎯 **Productivity Features**

* **Priority Filtering**: Focus on urgent emails and filter by type (meetings, issues, etc.)
* **Real-time Notifications**: Telegram alerts for truly urgent emails
* **Task Management**: Centralized to-do list extracted from your emails

### 🔧 **Personalization**

* **Custom Criteria**: Define what makes emails urgent or high-priority for you

## 🏗️ Architecture

### Core Components:

* **Backend**: Flask API with SQLAlchemy database
* **AI Pipeline**: LangGraph orchestrating Google Gemini 1.5 Pro
* **Frontend**: React.js with Tailwind CSS
* **Email Processing**: Postmark webhook integration
* **Database**: SQLite for email storage and metadata

## 🚀 Quick Start

### Prerequisites

* Python 3.8+
* Node.js 16+
* Postmark account
* Google Cloud account (for Gemini API)
* JIRA instance
* Google Calendar API credentials
* Telegram bot

### 1. Clone the Repository

```bash
git clone https://github.com/vartikatrao/MinimalizEmail
cd MinimalizEmail
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

### 5. Google Calendar Setup

> **Required** for meeting scheduling functionality.

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or use an existing one.
3. Enable the **Google Calendar API**.
4. Go to **APIs & Services > Credentials**:

   * Click **Create Credentials → OAuth client ID**
   * Choose **Desktop App** and download the `credentials.json` file.
5. Place `credentials.json` in the project root.
6. On first run, the app will open a browser window for OAuth authentication.

   * A `token.pkl` file will be saved for future use.

### 6. Telegram Bot Setup

> Used for real-time alerts on urgent emails.

1. Open [Telegram](https://telegram.org/) and search for **BotFather**.
2. Send `/newbot` and follow instructions to create your bot.
3. Note down the **Bot Token** provided.
4. Get your **Chat ID**:

   * Start a conversation with your bot.
   * Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   * Look for `chat.id` in the response JSON.
5. Add the following to your `.env`:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 7. Start the Backend

```bash
flask run
```

Backend will be available at `http://localhost:5000`

### 8. Frontend Setup

Frontend will be available at `http://localhost:3000/frontend/index.html`

9. Configure Postmark Webhook

In your Postmark account:

    Go to your server's Webhooks section

    Add inbound webhook URL: your publicly accessible URL (e.g., the one from ngrok) followed by /inbound
    Example: https://your-ngrok-id.ngrok-free.app/inbound

    Enable Inbound webhook

    Set up your inbound email address

    Note: During development, you can use ngrok to expose your local server to the internet. Start ngrok with ngrok http 5000 and use the generated HTTPS URL as your webhook URL in Postmark.

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

* **Demo**: [Youtube](https://youtu.be/jIBCTEd91SA)
* **GitHub Repository**: https://github.com/vartikatrao/MinimalizEmail
* **Postmark Challenge**: [https://dev.to/challenges/postmark](https://dev.to/challenges/postmark)

---

**Built with ❤️ for the Postmark Challenge**
