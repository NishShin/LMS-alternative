import flet as ft
import datetime


class StudentManager:
    
    def __init__(self, todo_view):
        self.todo = todo_view
    
    def update_student_dropdown(self):
        options = []
        for s in self.todo.students:
            if s.get('is_bridging', False):
                options.append(ft.dropdown.Option(s['email'], f"[B] {s['name']}"))
            else:
                options.append(ft.dropdown.Option(s['email'], s['name']))
        
        self.todo.student_dropdown.options = options
        self.todo.student_dropdown.options.insert(0, ft.dropdown.Option("__register__", "📝 Register New Account"))
        
        if self.todo.page:
            self.todo.page.update()
    
    def manage_students_dialog(self, e):
        
        students_list = ft.Column(scroll="auto", spacing=5)
        name_field = ft.TextField(label="Student Name", width=180)
        email_field = ft.TextField(label="Student Email", width=220)
        bridging_checkbox = ft.Checkbox(label="Bridging", value=False)
        
        def refresh_list():
            students_list.controls.clear()
            for student in self.todo.students:
                bridging_badge = "[B] " if student.get('is_bridging', False) else ""
                students_list.controls.append(
                    ft.Row([
                        ft.Text(f"{bridging_badge}{student['name']} ({student['email']})", expand=True),
                        ft.IconButton(
                            icon=ft.Icons.DELETE,
                            icon_color=ft.Colors.RED,
                            on_click=lambda e, s=student: remove_student(s),
                            tooltip="Remove student"
                        )
                    ])
                )
            self.todo.page.update()
        
        def add_student(e):
            if name_field.value and email_field.value:
                name = name_field.value.strip()
                email = email_field.value.strip()
                
                if name and email:
                    self.todo.students.append({
                        'name': name,
                        'email': email,
                        'is_bridging': bridging_checkbox.value
                    })
                    self.todo.data_manager.save_students(self.todo.students)
                    name_field.value = ""
                    email_field.value = ""
                    bridging_checkbox.value = False
                    refresh_list()
                    self.update_student_dropdown()
                    self.todo.show_snackbar("Student added", ft.Colors.GREEN)
        
        def remove_student(student):
            self.todo.students.remove(student)
            self.todo.data_manager.save_students(self.todo.students)
            refresh_list()
            self.update_student_dropdown()
            self.todo.show_snackbar("Student removed", ft.Colors.ORANGE)
        
        refresh_list()
        
        content = ft.Column([
            ft.Row([name_field, email_field, bridging_checkbox]),
            ft.ElevatedButton("Add Student", on_click=add_student, icon=ft.Icons.ADD),
            ft.Divider(),
            ft.Row([
                ft.Text("Current Students:", weight=ft.FontWeight.BOLD),
                ft.Text("[B] = Bridging Student", size=11, color=ft.Colors.GREY_600)
            ]),
            students_list
        ], width=550, height=400)
        
        overlay, close_overlay = self.todo.show_overlay(content, "Manage Students", width=600)
    
    def register_student_dialog(self, e=None):
        name_field = ft.TextField(label="Your Full Name", autofocus=True, width=300)
        email_field = ft.TextField(label="Your Email (Gmail required)", width=300)
        student_id_field = ft.TextField(label="Student ID (required)", width=300)
        bridging_switch = ft.Switch(label="I am a Bridging Student", value=False)
        error_text = ft.Text("", color=ft.Colors.RED, size=12)
        
        def do_register(e):
            name = name_field.value.strip() if name_field.value else ""
            email = email_field.value.strip() if email_field.value else ""
            student_id = student_id_field.value.strip() if student_id_field.value else ""
            is_bridging = bridging_switch.value
            

            if not name:
                error_text.value = "Please enter your full name"
                self.todo.page.update()
                return
            
            if not student_id:
                error_text.value = "Student ID is required"
                self.todo.page.update()
                return
            
            is_valid, error_msg = self._validate_email(email)
            if not is_valid:
                error_text.value = error_msg
                self.todo.page.update()
                return
            
            if not email.lower().endswith('@gmail.com'):
                error_text.value = "Only Gmail accounts are accepted"
                self.todo.page.update()
                return
            
            if any(s.get('email') == email for s in self.todo.students):
                error_text.value = "This email is already registered"
                self.todo.page.update()
                return
            
            new_student = {
                'name': name,
                'email': email,
                'student_id': student_id,
                'is_bridging': is_bridging,
                'registered_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            }
            
            self.todo.students.append(new_student)
            self.todo.data_manager.save_students(self.todo.students)
            
            student_type = "Bridging Student" if is_bridging else "Regular Student"
            
            close_overlay(e)
            
            self.update_student_dropdown()
            self.todo.student_dropdown.value = email
            self.todo.current_student_email = email
            
            self.todo.display_assignments()
            self.todo.show_snackbar(f"Welcome, {name}! Registered as {student_type}.", ft.Colors.GREEN)
        
        content = ft.Column([
            ft.Text("Register to access assignments and submit your work.", size=14),
            ft.Divider(),
            name_field,
            email_field,
            student_id_field,
            ft.Container(
                content=bridging_switch,
                padding=ft.padding.only(top=10, bottom=5)
            ),
            ft.Text("Bridging students are those transferring or taking additional courses.",
                   size=11, color=ft.Colors.GREY_600, italic=True),
            error_text,
            ft.Row([
                ft.TextButton("Cancel", on_click=lambda e: close_overlay(e)),
                ft.ElevatedButton(
                    "Register",
                    icon=ft.Icons.PERSON_ADD,
                    on_click=do_register
                )
            ], alignment=ft.MainAxisAlignment.END)
        ], spacing=10)
        
        overlay, close_overlay = self.todo.show_overlay(content, "📝 Student Registration", width=420)
    
    def _validate_email(self, email):
        if not email:
            return False, "Email is required"
        
        if "@" not in email or "." not in email:
            return False, "Invalid email format"
        
        for s in self.todo.students:
            if s['email'] == email:
                return False, "Email already registered"
        
        return True, ""
    
    def get_bridging_students(self):
        return [s for s in self.todo.students if s.get('is_bridging', False)]
    
    def get_regular_students(self):
        return [s for s in self.todo.students if not s.get('is_bridging', False)]