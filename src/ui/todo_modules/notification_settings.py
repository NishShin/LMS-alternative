import flet as ft


class NotificationSettings:
    
    def __init__(self, todo_view):
        self.todo = todo_view
    
    def show_notification_settings(self):
        if not self.todo.notification_service:
            self.todo.show_snackbar("Notification service not available", ft.Colors.RED)
            return
        
        gmail_enabled = self.todo.notification_service.gmail_enabled
        current_email = self.todo.notification_service.gmail_user or ""
        
        status_text = ft.Text(
            f"Gmail Notifications: {'✓ Enabled' if gmail_enabled else '✗ Disabled'}",
            color=ft.Colors.GREEN if gmail_enabled else ft.Colors.RED,
            weight=ft.FontWeight.BOLD
        )
        
        email_field = ft.TextField(
            label="Gmail Address",
            value=current_email,
            width=300,
            hint_text="your-email@gmail.com"
        )
        
        password_field = ft.TextField(
            label="App Password",
            password=True,
            can_reveal_password=True,
            width=300,
            hint_text="16-character app password"
        )
        
        info_text = ft.Text(
            "To use Gmail notifications:\n"
            "1. Enable 2-Step Verification in your Google Account\n"
            "2. Generate an App Password at: myaccount.google.com/apppasswords\n"
            "3. Enter your Gmail and the 16-character App Password above\n\n"
            "Students will receive emails when assignments are posted and grades are given.",
            size=11,
            color=ft.Colors.GREY_700
        )
        
        def save_gmail_config(e):
            email = email_field.value.strip()
            app_password = password_field.value.strip()
            
            if not email or not app_password:
                self.todo.show_snackbar("Please enter both email and app password", ft.Colors.RED)
                return
            
            if not email.endswith('@gmail.com'):
                self.todo.show_snackbar("Please use a Gmail address", ft.Colors.RED)
                return
            
            self.todo.notification_service.setup_gmail(email, app_password)
            
            test_result = self.todo.notification_service.send_email(
                email,
                "LMS Test Email",
                "Your Gmail integration is working correctly! You will now receive notifications for new assignments and grades."
            )
            
            if test_result:
                self.todo.show_snackbar("Gmail configured successfully! Check your inbox.", ft.Colors.GREEN)
                status_text.value = "Gmail Notifications: ✓ Enabled"
                status_text.color = ft.Colors.GREEN
            else:
                self.todo.show_snackbar("Failed to send test email. Check credentials.", ft.Colors.RED)
            
            self.todo.page.update()
        
        def disable_gmail(e):
            self.todo.notification_service.disable_gmail()
            status_text.value = "Gmail Notifications: ✗ Disabled"
            status_text.color = ft.Colors.RED
            email_field.value = ""
            password_field.value = ""
            self.todo.show_snackbar("Gmail notifications disabled", ft.Colors.ORANGE)
            self.todo.page.update()
        
        def test_email(e):
            if not self.todo.notification_service.gmail_enabled:
                self.todo.show_snackbar("Gmail not configured", ft.Colors.RED)
                return
            
            test_result = self.todo.notification_service.send_email(
                self.todo.notification_service.gmail_user,
                "LMS Test Email",
                "This is a test email from your Learning Management System."
            )
            
            if test_result:
                self.todo.show_snackbar("Test email sent! Check your inbox.", ft.Colors.GREEN)
            else:
                self.todo.show_snackbar("Failed to send test email", ft.Colors.RED)
        
        content = ft.Column([
            status_text,
            ft.Divider(),
            info_text,
            ft.Container(height=10),
            email_field,
            password_field,
            ft.Container(height=10),
            ft.Row([
                ft.ElevatedButton(
                    "Save & Test",
                    icon=ft.Icons.SAVE,
                    on_click=save_gmail_config,
                    bgcolor=ft.Colors.BLUE
                ),
                ft.ElevatedButton(
                    "Send Test Email",
                    icon=ft.Icons.EMAIL,
                    on_click=test_email,
                    disabled=not gmail_enabled
                ),
                ft.ElevatedButton(
                    "Disable",
                    icon=ft.Icons.CLOSE,
                    on_click=disable_gmail,
                    bgcolor=ft.Colors.RED,
                    color=ft.Colors.WHITE
                )
            ], spacing=10)
        ], width=450, spacing=10)
        
        overlay, close_overlay = self.todo.show_overlay(
            content,
            "📧 Notification Settings",
            width=500
        )