import flet as ft
import datetime


class SubmissionManager:

    def __init__(self, todo_view):
        self.todo = todo_view
        self.temp_file_path = None
        self.temp_file_name = None
        
        try:
            from services.file_preview_service import FilePreviewService
            self.file_preview = FilePreviewService(todo_view.page, todo_view.drive_service)
        except ImportError:
            self.file_preview = None
    
    def calculate_submission_timing(self, submitted_at_str, deadline_str):
        if not submitted_at_str or not deadline_str:
            return None, "No timing data"
        
        try:
            if 'T' in submitted_at_str:
                submitted_at = datetime.datetime.fromisoformat(submitted_at_str)
            else:
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
        subject = assignment.get('subject', 'Other')
        drive_folder_id = assignment.get('drive_folder_id')
        
        if not self.todo.drive_service:
            self.todo.show_snackbar("No Drive service available", ft.Colors.RED)
            return
        
        if not drive_folder_id:
            self.todo.show_snackbar("No submission folder linked to this assignment", ft.Colors.RED)
            return
        
        selected_folder_id = [drive_folder_id]
        
        drive_folder_name = self.todo.get_folder_name_by_id(drive_folder_id)
        folder_display = ft.Text(f"Upload to: {drive_folder_name}", size=13, color=ft.Colors.BLUE, overflow=ft.TextOverflow.VISIBLE, no_wrap=False)
        
        submission_text = ft.TextField(
            hint_text="Submission notes/comments",
            multiline=True,
            min_lines=3,
            expand=True
        )
        
        upload_status = ft.Text("", overflow=ft.TextOverflow.VISIBLE, no_wrap=False)
        
        def update_selected_folder(fid):
            selected_folder_id[0] = fid
            folder_name = self.todo.get_folder_name_by_id(fid)
            
            if folder_name == "Linked Folder" and self.todo.drive_service:
                try:
                    info = self.todo.drive_service.get_file_info(fid)
                    if info:
                        folder_name = info.get('name', 'Selected Folder')
                except:
                    folder_name = "Selected Folder"
            
            folder_display.value = f"Upload to: {folder_name}"
            self.todo.page.update()
        
        change_folder_btn = ft.TextButton(
            "Browse Folders",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=lambda e: self.todo.storage_manager.create_browse_dialog(
                selected_folder_id[0],
                update_selected_folder
            )
        )
        
        def on_file_picked(e: ft.FilePickerResultEvent):
            if not e.files:
                return
            
            file_path = e.files[0].path
            file_name = e.files[0].name
            
            student_name = self.todo.current_student_email.split('@')[0] if self.todo.current_student_email else "unknown"
            
            upload_status.value = f"Uploading {file_name}..."
            self.todo.page.update()
            
            try:
                result = self.todo.storage_manager.upload_submission_to_link_drive(
                    file_path,
                    file_name,
                    subject,
                    student_name,
                    selected_folder_id[0]
                )
                
                if result:
                    upload_status.value = f"✓ Uploaded to link drive"
                    self.todo.show_snackbar(f"File uploaded to link drive folder!", ft.Colors.GREEN)
                    
                    existing = self._get_submission_status(assignment['id'], self.todo.current_student_email)
                    submitted_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                    
                    notes = submission_text.value.strip() if submission_text.value else "Uploaded to link drive"
                    
                    if existing:
                        existing['submitted_at'] = submitted_at
                        existing['file_id'] = result.get('id')
                        existing['file_name'] = result.get('name')
                        existing['file_link'] = result.get('webViewLink')
                        existing['uploaded_to_drive'] = True
                        existing['submission_text'] = notes
                        existing['subject_folder'] = subject
                    else:
                        self.todo.submissions.append({
                            'id': str(datetime.datetime.now().timestamp()),
                            'assignment_id': assignment['id'],
                            'student_email': self.todo.current_student_email,
                            'submission_text': notes,
                            'submitted_at': submitted_at,
                            'grade': None,
                            'feedback': None,
                            'file_id': result.get('id'),
                            'file_name': result.get('name'),
                            'file_link': result.get('webViewLink'),
                            'uploaded_to_drive': True,
                            'subject_folder': subject
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
            ft.Text(f"Assignment: {assignment.get('title')}", weight=ft.FontWeight.BOLD, overflow=ft.TextOverflow.VISIBLE, no_wrap=False),
            ft.Text(f"Subject: {subject}", size=13, color=ft.Colors.BLUE, overflow=ft.TextOverflow.VISIBLE, no_wrap=False),
            ft.Divider(),
            submission_text,
            ft.Container(height=10),
            ft.ResponsiveRow([
                ft.Column(col={"sm": 12, "md": 8}, controls=[folder_display]),
                ft.Column(col={"sm": 12, "md": 4}, controls=[change_folder_btn])
            ]),
            ft.Text("You can browse and select a subfolder if needed", size=11, italic=True, color=ft.Colors.GREY_600, overflow=ft.TextOverflow.VISIBLE, no_wrap=False),
            ft.Container(height=5),
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
        ], spacing=10, scroll="auto")
        
        overlay, close_overlay = self.todo.show_overlay(
            content,
            f"Submit: {assignment['title']}",
            width=450
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

                grade_field = ft.TextField(
                    value=sub.get('grade', ''),
                    label="Grade",
                    col={"sm": 12, "md": 3},
                    border_color=ft.Colors.BLUE_400,
                    focused_border_color=ft.Colors.BLUE_700,
                    hint_text="Enter grade"
                )
                
                feedback_field = ft.TextField(
                    value=sub.get('feedback', ''),
                    label="Feedback",
                    col={"sm": 12, "md": 9},
                    multiline=True,
                    min_lines=2,
                    max_lines=4,
                    border_color=ft.Colors.BLUE_400,
                    focused_border_color=ft.Colors.BLUE_700,
                    hint_text="Enter feedback for student"
                )

                save_status = ft.Text("", size=12, overflow=ft.TextOverflow.VISIBLE, no_wrap=False)

                def make_save_grade_handler(submission, grade_field_ref, feedback_field_ref, status_text_ref):
                    def save_grade(e):
                        original_text = e.control.text
                        
                        e.control.disabled = True
                        e.control.text = "Saving..."
                        status_text_ref.value = "💾 Saving..."
                        status_text_ref.color = ft.Colors.BLUE
                        self.todo.page.update()
                        
                        try:
                            submission['grade'] = grade_field_ref.value
                            submission['feedback'] = feedback_field_ref.value
                            
                            submission['graded_at'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                            
                            self.todo.data_manager.save_submissions(self.todo.submissions)

                            if self.todo.notification_service and grade_field_ref.value:
                                self.todo.notification_service.notify_grade_posted(
                                    assignment, 
                                    submission['student_email'], 
                                    grade_field_ref.value,
                                    feedback_field_ref.value
                                )

                            status_text_ref.value = "Saved successfully!"
                            status_text_ref.color = ft.Colors.GREEN
                            e.control.text = original_text
                            e.control.disabled = False

                            if submission.get('grade'):
                                e.control.text = "Update Grade"

                            self.todo.show_snackbar(
                                f"✓ Grade saved for {student_name}",
                                ft.Colors.GREEN
                            )

                            import threading
                            def clear_status():
                                import time
                                time.sleep(2)
                                status_text_ref.value = ""
                                try:
                                    self.todo.page.update()
                                except:
                                    pass
                            
                            threading.Thread(target=clear_status, daemon=True).start()
                            
                        except Exception as ex:
                            status_text_ref.value = f"Error: {str(ex)}"
                            status_text_ref.color = ft.Colors.RED
                            e.control.text = original_text
                            e.control.disabled = False
                            
                            self.todo.show_snackbar(
                                f"✗ Failed to save grade: {str(ex)}",
                                ft.Colors.RED
                            )
                        
                        self.todo.page.update()
                    
                    return save_grade
                
                save_grade_handler = make_save_grade_handler(sub, grade_field, feedback_field, save_status)
                
                file_link_btn = ft.Container()
                if sub.get('file_link'):
                    file_link_btn = ft.ResponsiveRow([
                        ft.Column(col={"sm": 12, "md": 6}, controls=[
                            ft.TextButton(
                                "Preview File",
                                icon=ft.Icons.VISIBILITY,
                                on_click=lambda e, fid=sub.get('file_id'), fname=sub.get('file_name', 'File'): 
                                    self._preview_file(fid, fname) if self.file_preview and fid else None
                            ) if self.file_preview else ft.Container()
                        ]),
                        ft.Column(col={"sm": 12, "md": 6}, controls=[
                            ft.TextButton(
                                "Open in Browser",
                                icon=ft.Icons.OPEN_IN_NEW,
                                on_click=lambda e, link=sub['file_link']: self._open_link(link)
                            )
                        ])
                    ])
                elif sub.get('file_id') and self.todo.drive_service:
                    file_link_btn = ft.ResponsiveRow([
                        ft.Column(col={"sm": 12, "md": 6}, controls=[
                            ft.TextButton(
                                "Preview File",
                                icon=ft.Icons.VISIBILITY,
                                on_click=lambda e, fid=sub['file_id'], fname=sub.get('file_name', 'File'): 
                                    self._preview_file(fid, fname) if self.file_preview else None
                            ) if self.file_preview else ft.Container()
                        ]),
                        ft.Column(col={"sm": 12, "md": 6}, controls=[
                            ft.TextButton(
                                "Open in Browser",
                                icon=ft.Icons.OPEN_IN_NEW,
                                on_click=lambda e, fid=sub['file_id']: self._open_drive_file(fid)
                            )
                        ])
                    ])
                
                last_saved_container = ft.Container()
                if sub.get('graded_at'):
                    last_saved_container = ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.HISTORY, size=14, color=ft.Colors.GREY_600),
                            ft.Text(
                                f"Last updated: {sub.get('graded_at')}",
                                size=11,
                                color=ft.Colors.GREY_600,
                                italic=True,
                                overflow=ft.TextOverflow.VISIBLE,
                                no_wrap=False
                            )
                        ], spacing=5),
                        padding=ft.padding.only(top=5)
                    )
                
                button_text = "Update Grade" if sub.get('grade') else "Save Grade"
                button_icon = ft.Icons.UPDATE if sub.get('grade') else ft.Icons.SAVE
                
                edit_hint = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.EDIT, size=12, color=ft.Colors.BLUE_600),
                        ft.Text(
                            "You can edit and update grades anytime",
                            size=10,
                            color=ft.Colors.BLUE_600,
                            italic=True,
                            overflow=ft.TextOverflow.VISIBLE,
                            no_wrap=False
                        )
                    ], spacing=3),
                    padding=ft.padding.only(top=3),
                    visible=bool(sub.get('grade'))
                )
                
                card_content = ft.Column([
                    ft.Row([
                        status_icon,
                        ft.Text(f"{student_name} ({student['email']})", weight=ft.FontWeight.BOLD, overflow=ft.TextOverflow.VISIBLE, no_wrap=False),
                    ]),
                    ft.Text(status_text, size=12, color=ft.Colors.GREEN, overflow=ft.TextOverflow.VISIBLE, no_wrap=False),
                    ft.Container(
                        content=ft.Text(timing_text, size=13, weight=ft.FontWeight.BOLD, overflow=ft.TextOverflow.VISIBLE, no_wrap=False),
                        bgcolor=ft.Colors.with_opacity(0.1, timing_color),
                        padding=5,
                        border_radius=5
                    ) if timing_status else ft.Container(),
                    ft.Text(f"Notes: {sub.get('submission_text', 'No notes')}", size=12, overflow=ft.TextOverflow.VISIBLE, no_wrap=False),
                    ft.Text(
                        f"File: {sub.get('file_name', 'No file')}",
                        size=12,
                        color=ft.Colors.BLUE,
                        overflow=ft.TextOverflow.VISIBLE,
                        no_wrap=False
                    ),
                    file_link_btn,
                    ft.Divider(),
                    ft.Text("Grade & Feedback:", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                    ft.ResponsiveRow([grade_field, feedback_field]),
                    ft.Row([
                        ft.ElevatedButton(
                            button_text,
                            on_click=save_grade_handler,
                            icon=button_icon,
                            bgcolor=ft.Colors.BLUE,
                            color=ft.Colors.WHITE,
                            tooltip="Click to save or update grade and feedback"
                        ),
                        save_status
                    ], spacing=10),
                    edit_hint,
                    last_saved_container
                ])
                card_border_color = ft.Colors.GREEN_200
                card_bg = ft.Colors.GREEN_50
            else:
                status_icon = ft.Icon(ft.Icons.CANCEL, color=ft.Colors.RED)
                status_text = "Missing"
                card_content = ft.Row([
                    status_icon,
                    ft.Text(f"{student_name} ({student['email']})", weight=ft.FontWeight.BOLD, overflow=ft.TextOverflow.VISIBLE, no_wrap=False, expand=True),
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
            f"Submissions for: {assignment['title']} ({submitted_count}/{len(target_students)})",
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