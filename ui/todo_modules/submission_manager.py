import flet as ft
import datetime


class SubmissionManager:

    def __init__(self, todo_view):
        self.todo = todo_view
        self.temp_file_path = None
        self.temp_file_name = None
        
        try:
            from ui.todo_modules.file_preview import FilePreview
            self.file_preview = FilePreview(todo_view.page, todo_view.drive_service)
        except ImportError:
            self.file_preview = None
    
    def calculate_submission_timing(self, submitted_at_str, deadline_str):
        if not submitted_at_str or not deadline_str:
            return None, "No timing data"
        
        try:
            submitted_at = datetime.datetime.strptime(submitted_at_str, '%Y-%m-%d %H:%M')
            deadline = datetime.datetime.fromisoformat(deadline_str)
            
            time_diff = deadline - submitted_at
            
            if time_diff.total_seconds() > 0:
                days = time_diff.days
                hours = time_diff.seconds // 3600
                minutes = (time_diff.seconds % 3600) // 60
                
                if days > 0:
                    return "early", f"✅ {days}d {hours}h early"
                elif hours > 0:
                    return "early", f"✅ {hours}h {minutes}m early"
                else:
                    return "early", f"✅ {minutes}m early"
            else:
                time_diff = abs(time_diff)
                days = time_diff.days
                hours = time_diff.seconds // 3600
                minutes = (time_diff.seconds % 3600) // 60
                
                if days > 0:
                    return "late", f"⚠️ {days}d {hours}h late"
                elif hours > 0:
                    return "late", f"⚠️ {hours}h {minutes}m late"
                else:
                    return "late", f"⚠️ {minutes}m late"
        except:
            return None, "Invalid timing data"
    
    def submit_assignment_dialog(self, assignment):
        submission_text = ft.TextField(
            hint_text="Submission notes/comments",
            multiline=True,
            min_lines=3,
            width=350
        )
        
        uploaded_file_info = ft.Text("No file attached", size=12, italic=True)
        self.temp_file_path = None
        self.temp_file_name = None
        
        def on_file_picked(e: ft.FilePickerResultEvent):
            if e.files:
                self.temp_file_path = e.files[0].path
                self.temp_file_name = e.files[0].name
                uploaded_file_info.value = f"📎 Attached: {self.temp_file_name}"
                self.todo.page.update()
        
        file_picker = ft.FilePicker(on_result=on_file_picked)
        self.todo.page.overlay.append(file_picker)
        self.todo.page.update()
        
        upload_to_drive_checkbox = ft.Checkbox(
            label="Also upload to Google Drive folder",
            value=False,
            visible=bool(assignment.get('drive_folder_id') and self.todo.drive_service)
        )
        
        def submit(e):
            if not self.temp_file_path:
                self.todo.show_snackbar("Please attach a file", ft.Colors.RED)
                return
            
            existing = self._get_submission_status(assignment['id'], self.todo.current_student_email)
            submitted_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            
            sub_data = {
                'submission_text': submission_text.value,
                'submitted_at': submitted_at,
                'file_name': self.temp_file_name,
                'local_file_path': self.temp_file_path
            }
            
            if upload_to_drive_checkbox.value and self.todo.drive_service and assignment.get('drive_folder_id'):
                try:
                    self.todo.show_snackbar("Uploading to Drive...", ft.Colors.BLUE)
                    self.todo.page.update()
                    
                    student_name = self.todo.current_student_email.split('@')[0] if self.todo.current_student_email else "unknown"
                    new_filename = f"{student_name}_{self.temp_file_name}"
                    
                    result = self.todo.drive_service.upload_file(
                        self.temp_file_path,
                        parent_id=assignment.get('drive_folder_id'),
                        file_name=new_filename
                    )
                    
                    if result:
                        sub_data['file_id'] = result.get('id')
                        sub_data['file_link'] = result.get('webViewLink')
                        sub_data['uploaded_to_drive'] = True
                        self.todo.show_snackbar("File uploaded to Drive!", ft.Colors.GREEN)
                    else:
                        self.todo.show_snackbar("Drive upload failed, but submission saved locally", ft.Colors.ORANGE)
                except Exception as ex:
                    self.todo.show_snackbar(f"Drive upload error: {str(ex)}, but submission saved locally", ft.Colors.ORANGE)
            
            if existing:
                existing.update(sub_data)
            else:
                new_sub = {
                    'id': str(datetime.datetime.now().timestamp()),
                    'assignment_id': assignment['id'],
                    'student_email': self.todo.current_student_email,
                    'grade': None,
                    'feedback': None
                }
                new_sub.update(sub_data)
                self.todo.submissions.append(new_sub)
            
            self.todo.data_manager.save_submissions(self.todo.submissions)
            
            if self.todo.notification_service:
                student_name = self.todo.current_student_email.split('@')[0] if self.todo.current_student_email else "Student"
                self.todo.notification_service.notify_submission_received(assignment, student_name)
            
            close_overlay(e)
            self.todo.display_assignments()
            self.todo.show_snackbar("Assignment submitted successfully!", ft.Colors.GREEN)
        
        content = ft.Column([
            ft.Text("Submit your assignment:", size=14),
            submission_text,
            ft.Row([
                ft.ElevatedButton("Attach File", icon=ft.Icons.ATTACH_FILE, 
                                 on_click=lambda _: file_picker.pick_files()),
                ft.Container(content=uploaded_file_info, padding=ft.padding.only(left=10))
            ]),
            upload_to_drive_checkbox,
            ft.Container(height=10),
            ft.Row([
                ft.TextButton("Cancel", on_click=lambda e: close_overlay(e)),
                ft.ElevatedButton("Submit", on_click=submit, icon=ft.Icons.SEND)
            ], alignment=ft.MainAxisAlignment.END)
        ], spacing=10)
        
        overlay, close_overlay = self.todo.show_overlay(
            content,
            f"Submit: {assignment['title']}",
            width=450
        )
    
    def upload_to_drive_dialog(self, assignment):
        drive_folder_id = assignment.get('drive_folder_id')
        if not drive_folder_id or not self.todo.drive_service:
            self.todo.show_snackbar("No Drive folder linked", ft.Colors.RED)
            return
        
        initial_folder_name = self.todo.get_folder_name_by_id(drive_folder_id)
        
        selected_folder_id = [drive_folder_id]
        folder_display = ft.Text(f"Target: {initial_folder_name}", size=13)
        
        def update_folder(fid):
            selected_folder_id[0] = fid
            folder_name = self.todo.get_folder_name_by_id(fid)
            if folder_name == "Linked Folder" and self.todo.drive_service:
                try:
                    info = self.todo.drive_service.get_file_info(fid)
                    if info:
                        folder_name = info.get('name', 'Selected Folder')
                except:
                    folder_name = "Selected Folder"
            folder_display.value = f"Target: {folder_name}"
            self.todo.page.update()
        
        folder_selector = ft.Row([
            folder_display,
            ft.TextButton(
                "Change Folder",
                icon=ft.Icons.FOLDER_OPEN,
                on_click=lambda e: self.todo.storage_manager.create_browse_dialog(
                    drive_folder_id, update_folder
                )
            )
        ], spacing=10)
        
        upload_status = ft.Text("")
        
        def on_file_picked(e: ft.FilePickerResultEvent):
            if not e.files:
                return
            
            file_path = e.files[0].path
            file_name = e.files[0].name
            
            student_name = self.todo.current_student_email.split('@')[0] if self.todo.current_student_email else "unknown"
            
            upload_status.value = f"Uploading {file_name}..."
            self.todo.page.update()
            
            try:
                new_filename = f"{student_name}_{file_name}"
                target_folder_id = selected_folder_id[0]
                
                result = self.todo.drive_service.upload_file(
                    file_path,
                    parent_id=target_folder_id,
                    file_name=new_filename
                )
                
                if result:
                    upload_status.value = f"✓ Uploaded: {new_filename}"
                    self.todo.show_snackbar("File uploaded to Google Drive!", ft.Colors.GREEN)
                    
                    existing = self._get_submission_status(assignment['id'], self.todo.current_student_email)
                    submitted_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                    
                    if existing:
                        existing['submitted_at'] = submitted_at
                        existing['file_id'] = result.get('id')
                        existing['file_name'] = new_filename
                        existing['file_link'] = result.get('webViewLink')
                        existing['uploaded_to_drive'] = True
                    else:
                        self.todo.submissions.append({
                            'id': str(datetime.datetime.now().timestamp()),
                            'assignment_id': assignment['id'],
                            'student_email': self.todo.current_student_email,
                            'submission_text': "Uploaded directly to Drive",
                            'submitted_at': submitted_at,
                            'grade': None,
                            'feedback': None,
                            'file_id': result.get('id'),
                            'file_name': new_filename,
                            'file_link': result.get('webViewLink'),
                            'uploaded_to_drive': True
                        })
                    
                    self.todo.data_manager.save_submissions(self.todo.submissions)
                    self.todo.display_assignments()
                    
                    if self.todo.notification_service:
                        self.todo.notification_service.notify_submission_received(assignment, student_name)
                    
                    import time
                    time.sleep(1)
                    close_overlay(None)
                else:
                    upload_status.value = "✗ Upload failed"
                    self.todo.show_snackbar("Upload failed", ft.Colors.RED)
            except Exception as ex:
                upload_status.value = f"✗ Error: {str(ex)}"
                self.todo.show_snackbar(f"Error: {str(ex)}", ft.Colors.RED)
            
            self.todo.page.update()
        
        file_picker = ft.FilePicker(on_result=on_file_picked)
        self.todo.page.overlay.append(file_picker)
        self.todo.page.update()
        
        content = ft.Column([
            ft.Text(f"Assignment: {assignment.get('title')}", weight=ft.FontWeight.BOLD),
            ft.Divider(),
            folder_selector,
            ft.Text("Select a file to upload directly to the Google Drive folder.", size=14),
            ft.ElevatedButton(
                "Choose File",
                icon=ft.Icons.FILE_UPLOAD,
                on_click=lambda e: file_picker.pick_files()
            ),
            upload_status,
            ft.Container(height=10),
            ft.Row([
                ft.TextButton("Close", on_click=lambda e: close_overlay(e))
            ], alignment=ft.MainAxisAlignment.END)
        ], spacing=10)
        
        overlay, close_overlay = self.todo.show_overlay(
            content,
            "Upload to Drive",
            width=400
        )
    
    def view_submissions_dialog(self, assignment):
        submissions_list = ft.Column(scroll="auto", spacing=10)
        
        target = assignment.get('target_for', 'all')
        if target == 'bridging':
            target_students = self.todo.student_manager.get_bridging_students()
        elif target == 'regular':
            target_students = self.todo.student_manager.get_regular_students()
        else:
            target_students = self.todo.students
        
        if not target_students:
            submissions_list.controls.append(
                ft.Text("No students enrolled for this assignment type", color=ft.Colors.GREY)
            )
        
        submitted_count = 0
        deadline = assignment.get('deadline')
        
        for student in target_students:
            sub = next((s for s in self.todo.submissions
                       if s['assignment_id'] == assignment['id'] and s['student_email'] == student['email']), None)
            
            student_name = student['name']
            
            if sub:
                submitted_count += 1
                status_icon = ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN)
                status_text = f"Submitted: {sub['submitted_at']}"
                
                timing_status, timing_text = self.calculate_submission_timing(
                    sub['submitted_at'], 
                    deadline
                )
                timing_color = ft.Colors.GREEN if timing_status == "early" else ft.Colors.ORANGE
                
                grade_field = ft.TextField(value=sub.get('grade', ''), label="Grade", width=100)
                feedback_field = ft.TextField(
                    value=sub.get('feedback', ''),
                    label="Feedback",
                    multiline=True,
                    expand=True
                )
                
                def save_grade(e, s=sub, g=grade_field, f=feedback_field):
                    s['grade'] = g.value
                    s['feedback'] = f.value
                    self.todo.data_manager.save_submissions(self.todo.submissions)
                    
                    if self.todo.notification_service and g.value:
                        self.todo.notification_service.notify_grade_posted(
                            assignment, s['student_email'], g.value
                        )
                    
                    self.todo.show_snackbar("Grade saved", ft.Colors.BLUE)
                
                file_link_btn = ft.Container()
                if sub.get('file_link'):
                    file_link_btn = ft.Row([
                        ft.TextButton(
                            "Preview File",
                            icon=ft.Icons.VISIBILITY,
                            on_click=lambda e, fid=sub.get('file_id'), fname=sub.get('file_name', 'File'): 
                                self._preview_file(fid, fname) if self.file_preview and fid else None
                        ) if self.file_preview else ft.Container(),
                        ft.TextButton(
                            "Open in Browser",
                            icon=ft.Icons.OPEN_IN_NEW,
                            on_click=lambda e, link=sub['file_link']: self._open_link(link)
                        )
                    ])
                elif sub.get('file_id') and self.todo.drive_service:
                    file_link_btn = ft.Row([
                        ft.TextButton(
                            "Preview File",
                            icon=ft.Icons.VISIBILITY,
                            on_click=lambda e, fid=sub['file_id'], fname=sub.get('file_name', 'File'): 
                                self._preview_file(fid, fname) if self.file_preview else None
                        ) if self.file_preview else ft.Container(),
                        ft.TextButton(
                            "Open in Browser",
                            icon=ft.Icons.OPEN_IN_NEW,
                            on_click=lambda e, fid=sub['file_id']: self._open_drive_file(fid)
                        )
                    ])
                
                card_content = ft.Column([
                    ft.Row([
                        status_icon,
                        ft.Text(f"{student_name} ({student['email']})", weight=ft.FontWeight.BOLD),
                    ]),
                    ft.Text(status_text, size=12, color=ft.Colors.GREEN),
                    ft.Container(
                        content=ft.Text(timing_text, size=13, weight=ft.FontWeight.BOLD),
                        bgcolor=ft.Colors.with_opacity(0.1, timing_color),
                        padding=5,
                        border_radius=5
                    ) if timing_status else ft.Container(),
                    ft.Text(f"Notes: {sub.get('submission_text', 'No notes')}", size=12),
                    ft.Text(
                        f"File: {sub.get('file_name', 'No file')}",
                        size=12,
                        color=ft.Colors.BLUE
                    ),
                    file_link_btn,
                    ft.Divider(),
                    ft.Row([grade_field, feedback_field]),
                    ft.ElevatedButton("Save Grade", on_click=save_grade, icon=ft.Icons.SAVE)
                ])
                card_border_color = ft.Colors.GREEN_200
                card_bg = ft.Colors.GREEN_50
            else:
                status_icon = ft.Icon(ft.Icons.CANCEL, color=ft.Colors.RED)
                status_text = "Missing"
                card_content = ft.Row([
                    status_icon,
                    ft.Text(f"{student_name} ({student['email']})", weight=ft.FontWeight.BOLD),
                    ft.Text(status_text, color=ft.Colors.RED, weight=ft.FontWeight.BOLD)
                ])
                card_border_color = ft.Colors.RED_200
                card_bg = ft.Colors.RED_50
            
            card = ft.Container(
                content=card_content,
                padding=10,
                border=ft.border.all(1, card_border_color),
                border_radius=8,
                bgcolor=card_bg
            )
            submissions_list.controls.append(card)
        
        overlay, close_overlay = self.todo.show_overlay(
            submissions_list,
            f"Submissions: {assignment['title']} ({submitted_count}/{len(target_students)})",
            width=600,
            height=500
        )
    
    def _get_submission_status(self, assignment_id, student_email):
        for sub in self.todo.submissions:
            if sub['assignment_id'] == assignment_id and sub['student_email'] == student_email:
                return sub
        return None
    
    def _preview_file(self, file_id, file_name):
        if self.file_preview and file_id:
            self.file_preview.show_preview(file_id=file_id, file_name=file_name)
    
    def _open_link(self, link):
        import webbrowser
        webbrowser.open(link)
    
    def _open_drive_file(self, file_id):
        import webbrowser
        webbrowser.open(f"https://drive.google.com/file/d/{file_id}/view")