import os
import requests
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import json
#from dotenv import load_dotenv

# Load environment variables from the .env file
#load_dotenv()

def handler(event, context):
    # --- Config from Environment Variables ---
    TOKEN = os.environ.get("GITHUB_TOKEN")
    EMAIL_USER = os.environ.get("EMAIL_USER")
    EMAIL_PASS = os.environ.get("EMAIL_PASS")
    TO_EMAIL = os.environ.get("TO_EMAIL")
    REPORTER = os.environ.get("REPORTER_NAME")

    # Check if a reporter name is provided
    if not REPORTER:
        return {"statusCode": 400, "body": "REPORTER_NAME environment variable not set"}

    # --- GitHub API Query ---
    query = f"repo:urbanpiper/incidents is:issue is:open {REPORTER}"
    url = f"https://api.github.com/search/issues?q={query}"
    headers = {"Authorization": f"token {TOKEN}"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return {"statusCode": response.status_code, "body": f"GitHub API Error: {response.text}"}

    try:
        results = response.json().get("items", [])
    except json.JSONDecodeError:
        return {"statusCode": 500, "body": f"Invalid JSON response from GitHub: {response.text}"}

    # --- Check for stale issues (>2 days inactive) ---
    two_days_ago = datetime.utcnow() - timedelta(days=2)
    stale_issues = [
        issue["html_url"]
        for issue in results
        if datetime.strptime(issue["updated_at"], "%Y-%m-%dT%H:%M:%SZ") < two_days_ago
    ]

    # --- Send Email if stale issues found ---
    if stale_issues:
        subject = f"⚠️ Stale GitHub Incidents (>2 days old, reporter: {REPORTER})"
        body = "These incidents are still open and inactive:\n\n" + "\n".join(stale_issues)

        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = TO_EMAIL
        msg["Subject"] = Header(subject, "utf-8")
        msg.attach(MIMEText(body, "plain", "utf-8"))

        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(EMAIL_USER, EMAIL_PASS)
                server.sendmail(EMAIL_USER, TO_EMAIL, msg.as_string())
            return {"statusCode": 200,"headers": { "Content-Type": "application/json" },"body": json.dumps({ "message": "✅ Email sent" })}

        except Exception as e:
            return {"statusCode": 500, "body": f"❌ Email sending failed: {str(e)}"}
    else:
        return {"statusCode": 200, "body": "ℹ️ No stale issues found"}

#if __name__ == "__main__":
 #   response = handler(None, None)
  #  print(response)///