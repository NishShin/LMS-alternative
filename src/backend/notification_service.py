import json
import datetime
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


try:
    from plyer import notification as os_notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False
    print("plyer not installed - using in-app notifications only")


class NotificationService:
    def __init__(self, data_dir: Path = None, gmail_credentials: dict = None):
        self.data_dir = data_dir or Path("lms_data")
        self.data_dir.mkdir(exist_ok=True)
        self.notifications_file = self.data_dir / "notifications.json"
        self.notifications = self.load_notifications()
        
        self.gmail_enabled = False
        self.gmail_user = None
        self.gmail_password = None
        
        if gmail_credentials:
            self.setup_gmail(gmail_credentials.get('email'), gmail_credentials.get('app_password'))
        else:
            self._load_gmail_config()
    
    def _load_gmail_config(self):
        config_file = self.data_dir / "gmail_config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.setup_gmail(config.get('email'), config.get('app_password'))
            except Exception as e:
                print(f"Error loading Gmail config: {e}")
    
    def setup_gmail(self, email: str, app_password: str):
        if email and app_password:
            self.gmail_user = email
            self.gmail_password = app_password
            self.gmail_enabled = True
            self._save_gmail_config()
        else:
            self.gmail_enabled = False
    
    def _save_gmail_config(self):
        config_file = self.data_dir / "gmail_config.json"
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'email': self.gmail_user,
                    'app_password': self.gmail_password
                }, f, indent=2)
        except Exception as e:
            print(f"Error saving Gmail config: {e}")
    
    def disable_gmail(self):
        self.gmail_enabled = False
        self.gmail_user = None
        self.gmail_password = None
        config_file = self.data_dir / "gmail_config.json"
        if config_file.exists():
            os.remove(config_file)
    
    def send_email(self, to_email: str, subject: str, body: str, html: bool = False):
        if not self.gmail_enabled:
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.gmail_user
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(self.gmail_user, self.gmail_password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False
    
    def load_notifications(self):
        if self.notifications_file.exists():
            try:
                with open(self.notifications_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("notifications", [])
            except:
                pass
        return []
    
    def save_notifications(self):
        with open(self.notifications_file, 'w', encoding='utf-8') as f:
            json.dump({"notifications": self.notifications}, f, indent=2, ensure_ascii=False)
    
    def send_notification(self, title: str, message: str, student_email: str = None, assignment_id: str = None, notification_type: str = "info"):
        notification_record = {
            "id": str(datetime.datetime.now().timestamp()),
            "type": notification_type,
            "title": title,
            "message": message,
            "student_email": student_email,
            "assignment_id": assignment_id,
            "created_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
            "read": False
        }
        self.notifications.append(notification_record)
        self.save_notifications()
        
        if student_email and self.gmail_enabled:
            email_body = f"{title}\n\n{message}"
            self.send_email(student_email, title, email_body)
        
        if PLYER_AVAILABLE:
            try:
                os_notification.notify(
                    title=title,
                    message=message,
                    app_name="LMS Assignment Manager",
                    timeout=10
                )
                return True
            except Exception as e:
                print(f"OS notification failed: {e}")
        
        return False
    
    def notify_new_assignment(self, assignment: dict, students: list):
        title = f"New Assignment: {assignment.get('title', 'Untitled')}"
        
        deadline_str = assignment.get('deadline', 'No deadline')
        if deadline_str and deadline_str != 'No deadline':
            try:
                deadline_dt = datetime.datetime.fromisoformat(deadline_str)
                deadline_str = deadline_dt.strftime('%B %d, %Y at %I:%M %p')
            except:
                pass
        
        message = f"Subject: {assignment.get('subject', 'N/A')}\nDeadline: {deadline_str}"
        
        if assignment.get('description'):
            message += f"\n\nDescription:\n{assignment.get('description')}"
        
        os_notified = False
        
        for student in students:
            student_email = student.get('email')
            self.send_notification(
                title=title,
                message=message,
                student_email=student_email,
                assignment_id=assignment.get('id'),
                notification_type="new_assignment"
            )
            
            if not os_notified and PLYER_AVAILABLE:
                try:
                    os_notification.notify(
                        title=title,
                        message=f"{message}\nAssigned to {len(students)} students",
                        app_name="LMS Assignment Manager",
                        timeout=10
                    )
                    os_notified = True
                except:
                    pass
    
    def notify_deadline_reminder(self, assignment: dict, student_email: str, hours_remaining: int):
        title = f"⏰ Deadline Reminder: {assignment.get('title', 'Assignment')}"
        message = f"Only {hours_remaining} hours remaining to submit!"
        
        self.send_notification(
            title=title,
            message=message,
            student_email=student_email,
            assignment_id=assignment.get('id'),
            notification_type="deadline_reminder"
        )
    
    def notify_submission_received(self, assignment: dict, student_name: str):
        title = f"Submission Received"
        message = f"{student_name} submitted: {assignment.get('title', 'Assignment')}"
        
        self.send_notification(
            title=title,
            message=message,
            assignment_id=assignment.get('id'),
            notification_type="submission_received"
        )
    
    def notify_grade_posted(self, assignment: dict, student_email: str, grade: str, feedback: str = None):
        title = f"Grade Posted: {assignment.get('title', 'Assignment')}"
        message = f"Your grade: {grade}"
        
        if feedback:
            message += f"\n\nFeedback:\n{feedback}"
        
        self.send_notification(
            title=title,
            message=message,
            student_email=student_email,
            assignment_id=assignment.get('id'),
            notification_type="grade_posted"
        )
    
    def get_notifications_for_student(self, student_email: str):
        return [n for n in self.notifications 
                if n.get('student_email') == student_email or n.get('student_email') is None]
    
    def get_unread_count(self, student_email: str = None):
        if student_email:
            relevant = self.get_notifications_for_student(student_email)
        else:
            relevant = self.notifications
        return sum(1 for n in relevant if not n.get('read', False))
    
    def mark_as_read(self, notification_id: str):
        for n in self.notifications:
            if n.get('id') == notification_id:
                n['read'] = True
                self.save_notifications()
                return True
        return False
    
    def mark_all_as_read(self, student_email: str = None):
        for n in self.notifications:
            if student_email is None or n.get('student_email') == student_email:
                n['read'] = True
        self.save_notifications()
    
    def clear_old_notifications(self, days: int = 30):
        cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
        self.notifications = [
            n for n in self.notifications
            if datetime.datetime.strptime(n['created_at'], '%Y-%m-%d %H:%M') > cutoff
        ]
        self.save_notifications()