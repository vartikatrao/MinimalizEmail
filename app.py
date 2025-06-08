from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import json
import os
from typing import Dict, List, Optional
import threading
import time
import pytz

from typing import Annotated, Sequence, TypedDict
from dotenv import load_dotenv  
from langchain_core.messages import BaseMessage, ToolMessage, SystemMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
import requests 
import pickle
import datetime as dt
import dateparser
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///minimalize_email.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class AgentState(TypedDict, total=False):
    email_body: str
    email_subject: str
    email_to: str
    email_from: str
    email_tag: list[str]
    email_attachments: Sequence[str]
    email_reply: str
    meeting: str
    issue: str
    ticket_id: str
    ticket_url: str
    tool_call: bool
    messages: list[BaseMessage]  
    event_summary: str
    event_attendees: list[str]
    event_start: str
    event_end: str
    event_meet_link: str
    event_calendar_link: str
    ai_summary: str
    ai_reply: str
    extracted_tasks: list[dict[str, str | None]]

class Email(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_address = db.Column(db.String(255), nullable=False)
    to_address = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(500), nullable=False)
    body = db.Column(db.Text, nullable=False)
    text_body = db.Column(db.Text)
    html_body = db.Column(db.Text)
    received_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    processed_at = db.Column(db.DateTime)
    ai_summary = db.Column(db.Text)
    ai_reply = db.Column(db.Text)
    tags = db.Column(db.JSON)
    priority = db.Column(db.String(50))
    jira_ticket_id = db.Column(db.String(100))
    calendar_event_id = db.Column(db.String(100))
    calendar_event_link = db.Column(db.String(500))
    meet_link = db.Column(db.String(500))
    event_start_time = db.Column(db.DateTime)
    event_end_time = db.Column(db.DateTime)
    event_attendees = db.Column(db.JSON)
    is_processed = db.Column(db.Boolean, default=False)
    processing_error = db.Column(db.Text)

class UserPreferences(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), nullable=False, unique=True)
    work_summary = db.Column(db.Text)
    urgent_criteria = db.Column(db.Text)
    high_priority_criteria = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email_id = db.Column(db.Integer, db.ForeignKey('email.id'), nullable=True)
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    priority = db.Column(db.String(50), default='normal')
    status = db.Column(db.String(50), default='pending')
    due_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime)
    email = db.relationship('Email', backref=db.backref('tasks', lazy=True))

os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
vanilla_model = ChatGoogleGenerativeAI(model="models/gemini-1.5-pro-latest", temperature=0.3)

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

JIRA_DOMAIN = os.getenv('JIRA_DOMAIN')
JIRA_PROJECT_KEY = os.getenv('JIRA_PROJECT_KEY')
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

SCOPES = ['https://www.googleapis.com/auth/calendar']
def priority_check(state: AgentState) -> str:
    if "urgent" in state.get("email_tag", []):
        return "notify"
    return "skip"

def send_telegram_alert(state: AgentState) -> AgentState:
    email_subject = state.get("email_subject", "No Subject")
    email_body = state.get("email_body", "No Body")
    prompt = (
        f"You're an alert system. Generate a short, high-priority alert message "
        f"based on the following email.\n\n"
        f"Subject: {email_subject}\n"
        f"Body: {email_body}\n\n"
        f"Respond only with the alert message."
    )
    generated_alert = vanilla_model.invoke(prompt).content.strip()
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": generated_alert,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("✅ Telegram alert sent.")
    else:
        print("❌ Telegram alert failed:", response.text)
    return state

def classify_email(state: AgentState) -> AgentState:
    # Fetch user preferences if available
    user_id = "default_user"
    prefs = UserPreferences.query.filter_by(user_id=user_id).first()
    urgent_criteria = prefs.urgent_criteria if prefs and prefs.urgent_criteria else ""
    high_priority_criteria = prefs.high_priority_criteria if prefs and prefs.high_priority_criteria else ""

    system_message = (
        "You are a helpful assistant that classifies emails based on their content. "
        "Classify the email into one of these categories: 'urgent', 'high_priority', "
        "'low_priority', 'spam', or 'other'. Just return the tag."
    )
    if urgent_criteria or high_priority_criteria:
        system_message += (
            "\n\nUser preferences for classification:\n"
            f"- Urgent criteria: {urgent_criteria}\n"
            f"- High priority criteria: {high_priority_criteria}\n"
            "Use these preferences to improve your classification."
        )

    messages = [
        SystemMessage(content=system_message),
        HumanMessage(content=f"Classify this email:\n\n{state['email_body']}")
    ]

    response = vanilla_model.invoke(messages)
    classification = response.content.strip()
    
    if "email_tag" not in state or state["email_tag"] is None:
        state["email_tag"] = []
    state["email_tag"].append(classification)
    print(f"📧 Classified email as: {classification}")
    return state

def get_calendar_service():
    creds = None
    if os.path.exists('token.pkl'):
        with open('token.pkl', 'rb') as token:
            creds = pickle.load(token)
    else:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.pkl', 'wb') as token:
            pickle.dump(creds, token)
    return build('calendar', 'v3', credentials=creds)


@tool
def create_calendar_event(
    meeting: str,
    time_description: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    sender_email: Optional[str] = None,
) -> dict:
    """Create a Google Calendar event with optional time and attendees.

    Args:
        meeting (str): Description of the meeting.
        time_description (Optional[str]): Time like 'tomorrow at 5pm'.
        attendees (Optional[List[str]]): Attendee email list.
        sender_email (Optional[str]): Email of the sender (to be added as an attendee).

    Returns:
        dict: Summary, event ID, event link, and meet link.
    """
    service = get_calendar_service()
    tz = pytz.timezone("Asia/Kolkata")

    print(f"Creating calendar event for meeting: {meeting}")
    print(f"Time description: {time_description}")
    print(f"Attendees: {attendees}")
    print(f"Sender email: {sender_email}")

    if time_description:
        start_time = dateparser.parse(
            time_description,
            settings={
                "TIMEZONE": "Asia/Kolkata",
                "RETURN_AS_TIMEZONE_AWARE": True,
                "TO_TIMEZONE": "Asia/Kolkata",
                "PREFER_DATES_FROM": "future"
            }
        )
    if not start_time:
        raise ValueError(f"Invalid time format: {time_description}")

    print(f"Parsed start time: {start_time}")

    end_time = start_time + dt.timedelta(hours=1)

    attendees = set(attendees or [])
    if sender_email:
        attendees.add(sender_email)

    event = {
        'summary': meeting,
        'start': {
            'dateTime': start_time.isoformat(),
        },
        'end': {
            'dateTime': end_time.isoformat(),
        },
        'attendees': [{'email': email} for email in attendees],
        'conferenceData': {
            'createRequest': {
                'requestId': f"meet-{dt.datetime.now().timestamp()}",
                'conferenceSolutionKey': {
                    'type': 'hangoutsMeet'
                },
            }
        },
    }

    created_event = service.events().insert(
        calendarId='primary',
        body=event,
        conferenceDataVersion=1
    ).execute()

    print(f"✅ Created calendar event: {created_event.get('htmlLink')}")
    print("Start time (ISO):", created_event['start']['dateTime'])
    print("End time (ISO):", created_event['end']['dateTime'])


    return {
        "event_summary": meeting,
        "event_id": created_event.get("id"),
        "event_link": created_event.get("htmlLink"),
        "event_attendees": list(attendees),
        "event_start": created_event['start']['dateTime'],
        "event_end": created_event['end']['dateTime'],
        "event_meet_link": created_event.get('conferenceData', {}).get('entryPoints', [{}])[0].get('uri'),
        "event_calendar_link": created_event.get('htmlLink')
    }

@tool
def create_jira_ticket(issue: str) -> dict:
    """Create a JIRA ticket for the given issue."""
    url = f"https://{JIRA_DOMAIN}/rest/api/3/issue"
    auth = (JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    payload = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": issue,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": issue
                            }
                        ]
                    }
                ]
            },
            "issuetype": {"name": "Task"}
        }
    }

    response = requests.post(url, json=payload, headers=headers, auth=auth)

    if response.status_code == 201:
        issue_key = response.json()["key"]
        print(f"✅ Created JIRA ticket: {issue_key}")
        ticket_url = f"https://{JIRA_DOMAIN}/browse/{issue_key}"
        return {"ticket_id": issue_key, "ticket_url": ticket_url}
    else:
        return {"error": "Failed to create issue"}

def store_tool_outputs(state: AgentState) -> AgentState:
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, ToolMessage):
            try:
                content_dict = json.loads(msg.content)
                if "ticket_id" in content_dict:
                    state["ticket_id"] = content_dict["ticket_id"]
                    state["ticket_url"] = content_dict.get("ticket_url", "")
                    if "email_tag" not in state:
                        state["email_tag"] = []
                    state["email_tag"].append("issue")
                if "event_summary" in content_dict:
                    state["event_summary"] = content_dict["event_summary"]
                    if state.get("email_from") not in content_dict.get("event_attendees", []):
                        if state.get("event_attendees") is None:
                            state["event_attendees"] = []
                        state["event_attendees"].append(state.get("email_from", ""))
                    state["event_start"] = content_dict.get("event_start")
                    state["event_end"] = content_dict.get("event_end")
                    state["event_meet_link"] = content_dict.get("event_meet_link")
                    state["event_calendar_link"] = content_dict.get("event_calendar_link")
                    if "email_tag" not in state:
                        state["email_tag"] = []
                    state["email_tag"].append("meeting")
            except Exception as e:
                print(f"❌ Failed to parse ToolMessage content: {msg.content} | Error: {e}")
    return state

tools = [create_calendar_event, create_jira_ticket]
model = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro-latest",
    temperature=0.1
).bind_tools(tools)

def model_call(state: AgentState) -> AgentState:
    message_history = state.get("messages", [])
    new_messages = [
        SystemMessage(
            content="You are a helpful assistant that calls relevant tools based on the email content. "
                    "If the email talks about a meeting, create a calendar event. If it mentions an issue, create a JIRA ticket."
        ),
        HumanMessage(
            content=f"Email:\nSubject: {state.get('email_subject', '')}\n\n{state['email_body']}"
        )
    ]

    response = model.invoke(new_messages)
    state["messages"] = add_messages(message_history, [response])

    if isinstance(response, AIMessage) and getattr(response, "tool_calls", None):
        state["tool_call"] = True

    return state

def generate_reply(state: AgentState) -> AgentState:
    email_subject = state.get("email_subject", "No subject")
    email_body = state.get("email_body", "No body")

    ticket_id = state.get("ticket_id")
    meeting_summary = state.get("event_summary")
    meeting_time = state.get("event_start")
    meet_link = state.get("event_meet_link")

    ticket_info = f"A JIRA ticket has been created with ID: *{ticket_id}*." if ticket_id else ""
    meeting_info = (
        f"A meeting has been scheduled to discuss this:\n"
        f"- Topic: *{meeting_summary}*\n"
        f"- Time: {meeting_time}\n"
        f"- Link: {meet_link}"
        if meeting_summary and meeting_time and meet_link
        else ""
    )

    context_parts = [part for part in [ticket_info, meeting_info] if part]
    if not context_parts:
        context_parts = ["We are reviewing your message and will get back to you shortly."]

    context = "\n\n".join(context_parts)

    prompt = (
        "You're a helpful assistant drafting a professional reply to an email.\n\n"
        f"Original email:\nSubject: {email_subject}\nBody: {email_body}\n\n"
        f"Reply to the sender politely, using the following information:\n{context}\n\n"
        "Respond only with the reply body."
    )

    response = vanilla_model.invoke(prompt)
    reply = response.content.strip()
    print(f"✉️ Generated reply: {reply}")
    state["email_reply"] = reply
    return state

def generate_summary(state: AgentState) -> AgentState:
    """Generate a concise summary of the email"""
    email_subject = state.get("email_subject", "No subject")
    email_body = state.get("email_body", "No body")
    
    prompt = (
        "Generate a concise 1-2 sentence summary of this email:\n\n"
        f"Subject: {email_subject}\n"
        f"Body: {email_body}\n\n"
        "Focus on the main action items or key information."
    )
    
    response = vanilla_model.invoke(prompt)
    summary = response.content.strip()
    state["ai_summary"] = summary
    print(f"📄 Generated summary: {summary}")
    return state

def extract_tasks(state: AgentState) -> AgentState:
    """Extract tasks from the email body and create Task objects"""
    email_body = state.get("email_body", "")
    email_subject = state.get("email_subject", "No subject")
    prompt = (
        "You are a task extraction assistant. Analyze this email and extract any actionable tasks or to-dos.\n"
        "Return the tasks as a JSON array. Each task should have:\n"
        "- title: Brief description of the task\n"
        "- description: Detailed description if needed\n"
        "- priority: 'high', 'normal', or 'low'\n"
        "- due_date: If mentioned in the email (in ISO format), otherwise null\n\n"
        f"Subject: {email_subject}\n"
        f"Body: {email_body}\n\n"
        "Examples of tasks to extract:\n"
        "- 'Please review the document by Friday'\n"
        "- 'Schedule a meeting with the team'\n"
        "- 'Send the report to management'\n"
        "- 'Follow up on the client request'\n\n"
        "If no actionable tasks are found, return an empty array [].\n"
        "Respond only with valid JSON."
    )
    try:
        response = vanilla_model.invoke(prompt)
        tasks_json = response.content.strip()
        
        # Clean up the response to ensure it's valid JSON
        if tasks_json.startswith('```json'):
            tasks_json = tasks_json[7:-3].strip()
        elif tasks_json.startswith('```'):
            tasks_json = tasks_json[3:-3].strip()
        
        tasks = json.loads(tasks_json)
        state["extracted_tasks"] = tasks if isinstance(tasks, list) else []
        print(f"📋 Extracted {len(state['extracted_tasks'])} tasks")
        
    except Exception as e:
        print(f"❌ Error extracting tasks: {e}")
        state["extracted_tasks"] = []
    
    return state


# Build the LangGraph
tool_node = ToolNode(tools=tools)
graph = StateGraph(AgentState)

graph.add_node("classify_email", classify_email)
graph.add_node("send_notification", send_telegram_alert)
graph.add_node("model_call", model_call)
graph.add_node("tools", tool_node)
graph.add_node("store_tool_outputs", store_tool_outputs)
graph.add_node("generate_reply", generate_reply)
graph.add_node("generate_summary", generate_summary)
graph.add_node("extract_tasks", extract_tasks)

graph.add_edge(START, "classify_email")
graph.add_conditional_edges("classify_email", priority_check, {
    "notify": "send_notification",
    "skip": "model_call"
})
graph.add_edge("send_notification", "model_call")
graph.add_conditional_edges(
    "model_call",
    lambda state: "tools" if state.get("tool_call") else "generate_summary"
)
graph.add_edge("tools", "store_tool_outputs")
graph.add_edge("store_tool_outputs", "generate_summary")
graph.add_edge("generate_summary", "generate_reply")
graph.add_edge("generate_reply", "extract_tasks")
graph.add_edge("extract_tasks", END)
email_processor = graph.compile()

def process_email_async(email_id: int):
    try:
        with app.app_context():
            email = Email.query.get(email_id)
            if not email:
                return
            inputs = {
                "email_body": email.body or email.text_body,
                "email_subject": email.subject,
                "email_from": email.from_address,
                "email_to": email.to_address
            }
            result = email_processor.invoke(inputs)
            print(f"📧 Processing email {email_id} with LangGraph...")
            print(f"Result: {result}")
            email.ai_summary = result.get("ai_summary", "")
            email.ai_reply = result.get("email_reply", "")
            email.tags = result.get("email_tag", [])
            email.priority = "urgent" if "urgent" in result.get("email_tag", []) else "normal"
            email.jira_ticket_id = result.get("ticket_id")
            email.calendar_event_id = result.get("event_summary")
            email.calendar_event_link = result.get("event_calendar_link") if "event_calendar_link" in result else None
            email.meet_link = result.get("event_meet_link")
            if result.get("event_start"):
                try:
                    email.event_start_time = datetime.fromisoformat(result["event_start"].replace('Z', '+00:00'))
                except:
                    pass
            if result.get("event_end"):
                try:
                    email.event_end_time = datetime.fromisoformat(result["event_end"].replace('Z', '+00:00'))
                except:
                    pass
            email.event_attendees = result.get("event_attendees", [])
            extracted_tasks = result.get("extracted_tasks", [])
            for task_data in extracted_tasks:
                task = Task(
                    email_id=email.id,
                    title=task_data.get("title", ""),
                    description=task_data.get("description", ""),
                    priority=task_data.get("priority", "normal"),
                    due_date=datetime.fromisoformat(task_data["due_date"]) if task_data.get("due_date") else None
                )
                db.session.add(task)
            email.is_processed = True
            email.processed_at = datetime.now(timezone.utc)
            db.session.commit()
            print(f"✅ Email {email_id} processed successfully")
    except Exception as e:
        with app.app_context():
            email = Email.query.get(email_id)
            if email:
                email.processing_error = str(e)
                email.is_processed = True
                email.processed_at = datetime.now(timezone.utc)
                db.session.commit()
        print(f"❌ Error processing email {email_id}: {e}")

def format_email_for_api(email: Email) -> Dict:
    return {
        "id": email.id,
        "from": email.from_address,
        "to": email.to_address,
        "subject": email.subject,
        "body": email.body or email.text_body,
        "html_body": email.html_body,
        "received_at": email.received_at.isoformat(),
        "processed_at": email.processed_at.isoformat() if email.processed_at else None,
        "ai_summary": email.ai_summary,
        "ai_reply": email.ai_reply,
        "tags": email.tags or [],
        "priority": email.priority,
        "jira_ticket": {
            "ticket_id": email.jira_ticket_id,
            "url": f"https://{JIRA_DOMAIN}/browse/{email.jira_ticket_id}" if email.jira_ticket_id else None,
            "status": "Open"
        } if email.jira_ticket_id else None,
        "calendar_event": {
            "title": email.calendar_event_id,
            "start_time": email.event_start_time.isoformat() if email.event_start_time else None,
            "end_time": email.event_end_time.isoformat() if email.event_end_time else None,
            "attendees": email.event_attendees or [],
            "meet_link": email.meet_link,
            "calendar_link": email.calendar_event_link
        } if email.calendar_event_id else None,
        "is_processed": email.is_processed,
        "processing_error": email.processing_error
    }

@app.route('/inbound', methods=['POST'])
def handle_inbound_email():
    try:
        data = request.json
        email = Email(
            from_address=data.get('From', ''),
            to_address=data.get('To', ''),
            subject=data.get('Subject', ''),
            body=data.get('HtmlBody', ''),
            text_body=data.get('TextBody', ''),
            html_body=data.get('HtmlBody', ''),
            received_at=datetime.now(timezone.utc)
        )
        db.session.add(email)
        db.session.commit()
        threading.Thread(
            target=process_email_async,
            args=(email.id,),
            daemon=True
        ).start()
        print(f"✅ Email received and queued for processing: {email.subject}")
        return jsonify({"status": "received", "email_id": email.id}), 200
    except Exception as e:
        print(f"❌ Error handling inbound email: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/emails', methods=['GET'])
def get_emails():
    try:
        filter_type = request.args.get('filter', 'all')
        if filter_type == 'all':
            emails = Email.query.filter_by(is_processed=True).order_by(Email.received_at.desc()).limit(50).all()
        else:
            all_emails = Email.query.filter_by(is_processed=True).order_by(Email.received_at.desc()).all()
            filtered_emails = []
            for email in all_emails:
                tags = email.tags or []
                if filter_type == 'urgent':
                    if 'urgent' in tags or email.priority == 'urgent':
                        filtered_emails.append(email)
                elif filter_type == 'high-priority':
                    if 'high_priority' in tags or 'high-priority' in tags:
                        filtered_emails.append(email)
                elif filter_type == 'low-priority':
                    if 'low_priority' in tags or 'low-priority' in tags:
                        filtered_emails.append(email)
                elif filter_type == 'meeting':
                    if 'meeting' in tags or email.calendar_event_id:
                        filtered_emails.append(email)
                elif filter_type == 'issue':
                    if 'issue' in tags or email.jira_ticket_id:
                        filtered_emails.append(email)
                elif filter_type in tags:
                    filtered_emails.append(email)
            emails = filtered_emails[:50]
        return jsonify([format_email_for_api(email) for email in emails])
    except Exception as e:
        print(f"Error in get_emails: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/emails/<int:email_id>', methods=['GET'])
def get_email_details(email_id):
    try:
        email = Email.query.get_or_404(email_id)
        return jsonify(format_email_for_api(email))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/emails/<int:email_id>/reply', methods=['POST'])
def send_email_reply(email_id):
    try:
        data = request.json
        reply_content = data.get('reply', '')
        if not reply_content:
            return jsonify({"error": "Reply content is required"}), 400
        email = Email.query.get_or_404(email_id)
        print(f"📧 Sending reply to {email.from_address}")
        print(f"Subject: Re: {email.subject}")
        print(f"Body: {reply_content}")
        return jsonify({"status": "sent", "message": "Reply sent successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
        # TODO: Implement actual email sending via Postmark
        # postmark_client.emails.send(
        #     From="your-email@domain.com",
        #     To=email.from_address,
        #     Subject=f"Re: {email.subject}",
        #     TextBody=reply_content
        # )
        
        return jsonify({"status": "sent", "message": "Reply sent successfully"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/user/preferences', methods=['POST'])
def save_user_preferences():
    """Save user preferences from setup"""
    try:
        data = request.json
        
        user_id = "default_user"
        
        prefs = UserPreferences.query.filter_by(user_id=user_id).first()
        if not prefs:
            prefs = UserPreferences(user_id=user_id)
        
        prefs.work_summary = data.get('workSummary', '')
        prefs.urgent_criteria = data.get('urgentEmails', '')
        prefs.high_priority_criteria = data.get('highPriorityEmails', '')
        prefs.updated_at = datetime.now(timezone.utc)
        
        db.session.add(prefs)
        db.session.commit()
        
        return jsonify({"status": "saved", "message": "Preferences saved successfully"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/user/preferences', methods=['GET'])
def get_user_preferences():
    """Get user preferences"""
    try:
        user_id = "default_user"
        prefs = UserPreferences.query.filter_by(user_id=user_id).first()
        
        if not prefs:
            return jsonify({})
        
        return jsonify({
            "workSummary": prefs.work_summary,
            "urgentEmails": prefs.urgent_criteria,
            "highPriorityEmails": prefs.high_priority_criteria
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_email_stats():
    """Get email statistics for dashboard"""
    try:
        total_emails = Email.query.count()
        processed_emails = Email.query.filter_by(is_processed=True).count()
        urgent_emails = Email.query.filter(Email.tags.contains(['urgent'])).count()
        tickets_created = Email.query.filter(Email.jira_ticket_id.isnot(None)).count()
        meetings_scheduled = Email.query.filter(Email.calendar_event_id.isnot(None)).count()
        
        return jsonify({
            "total_emails": total_emails,
            "processed_emails": processed_emails,
            "urgent_emails": urgent_emails,
            "tickets_created": tickets_created,
            "meetings_scheduled": meetings_scheduled
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Get all tasks with optional filtering"""
    try:
        status = request.args.get('status', 'all')  # all, pending, completed
        priority = request.args.get('priority', 'all')  # all, high, normal, low
        
        query = Task.query
        
        if status != 'all':
            query = query.filter_by(status=status)
        
        if priority != 'all':
            query = query.filter_by(priority=priority)
        
        tasks = query.order_by(Task.created_at.desc()).all()
        
        task_list = []
        for task in tasks:
            task_list.append({
                "id": task.id,
                "email_id": task.email_id,
                "title": task.title,
                "description": task.description,
                "priority": task.priority,
                "status": task.status,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "created_at": task.created_at.isoformat(),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "email_subject": task.email.subject if task.email else None,
                "email_from": task.email.from_address if task.email else None
            })
        
        return jsonify(task_list)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks/<int:task_id>/toggle', methods=['POST'])
def toggle_task_status(task_id):
    """Toggle task completion status"""
    try:
        task = Task.query.get_or_404(task_id)
        
        if task.status == 'completed':
            task.status = 'pending'
            task.completed_at = None
        else:
            task.status = 'completed'
            task.completed_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        return jsonify({
            "id": task.id,
            "status": task.status,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Create a new task manually"""
    try:
        data = request.json
        
        task = Task(
            email_id=data.get('email_id'),  # Optional
            title=data.get('title'),
            description=data.get('description', ''),
            priority=data.get('priority', 'normal'),
            due_date=datetime.fromisoformat(data['due_date']) if data.get('due_date') else None
        )
        
        db.session.add(task)
        db.session.commit()
        
        return jsonify({
            "id": task.id,
            "message": "Task created successfully"
        })
        
    except Exception as e:
        print(f"Error creating task: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task"""
    try:
        task = Task.query.get_or_404(task_id)
        db.session.delete(task)
        db.session.commit()
        
        return jsonify({"message": "Task deleted successfully"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks/stats', methods=['GET'])
def get_task_stats():
    """Get task statistics"""
    try:
        total_tasks = Task.query.count()
        pending_tasks = Task.query.filter_by(status='pending').count()
        completed_tasks = Task.query.filter_by(status='completed').count()
        high_priority_tasks = Task.query.filter_by(priority='high', status='pending').count()
        
        # Tasks due today or overdue
        today = datetime.now(timezone.utc).date()
        overdue_tasks = Task.query.filter(
            Task.due_date < datetime.now(timezone.utc),
            Task.status == 'pending'
        ).count()
        
        return jsonify({
            "total_tasks": total_tasks,
            "pending_tasks": pending_tasks,
            "completed_tasks": completed_tasks,
            "high_priority_tasks": high_priority_tasks,
            "overdue_tasks": overdue_tasks
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()})


@app.cli.command("init-db")
def init_db_command():
    """Clear existing data and create new tables."""
    db.create_all()
    print("✅ Initialized the database.")


if __name__ == '__main__':
    
    print("🚀 MinimalizEmail backend starting...")
    print("📧 Postmark webhook endpoint: http://localhost:5000/inbound")
    print("🌐 API base URL: http://localhost:5000/api")
    
    app.run(host='0.0.0.0', port=5000, debug=True)