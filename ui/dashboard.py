import flet as ft
from services.drive_service import DriveService

class Dashboard(ft.Control):
    """Main dashboard view with file listing"""
    
    def __init__(self, page, auth_service, on_logout):
        super().__init__()
        self.page = page
        self.auth = auth_service
        self.on_logout = on_logout
        self.drive = DriveService(auth_service.get_service())
        
        self.current_folder_id = 'root'
        self.folder_stack = []  # For navigation history
        self.selected_files = set()
        
        # UI Components
        self.file_list = ft.ListView(expand=True, spacing=2)
        self.current_path = ft.Text("My Drive", size=18, weight=ft.FontWeight.BOLD)
        self.status_bar = ft.Text("Ready", size=12, color=ft.colors.GREY_700)
        self.search_field = ft.TextField(
            hint_text="Search files...",
            prefix_icon=ft.icons.SEARCH,
            on_submit=self.handle_search,
            width=300
        )
        
        # Get user info
        user_info = self.auth.get_user_info()
        self.user_email = user_info.get('emailAddress', 'User') if user_info else 'User'
        
        # Load initial files
        self.load_files()
    
    def load_files(self, folder_id=None):
        """Load files from current folder"""
        if folder_id:
            self.current_folder_id = folder_id
        
        self.status_bar.value = "Loading files..."
        self.update()
        
        result = self.drive.list_files(self.current_folder_id)
        files = result['files']
        
        self.file_list.controls.clear()
        self.selected_files.clear()
        
        # Add back button if not in root
        if self.current_folder_id != 'root':
            back_button = ft.ListTile(
                leading=ft.Icon(ft.icons.ARROW_BACK, color=ft.colors.BLUE),
                title=ft.Text(".. (Back)", weight=ft.FontWeight.BOLD),
                on_click=self.go_back
            )
            self.file_list.controls.append(back_button)
        
        # Add files
        for file in files:
            self.file_list.controls.append(self.create_file_tile(file))
        
        if len(files) == 0 and self.current_folder_id == 'root':
            self.file_list.controls.append(
                ft.Container(
                    content=ft.Text(
                        "No files found in My Drive",
                        size=16,
                        color=ft.colors.GREY_500
                    ),
                    padding=20,
                    alignment=ft.alignment.center
                )
            )
        
        self.status_bar.value = f"Loaded {len(files)} items"
        self.update()
    
    def create_file_tile(self, file):
        """Create a list tile for a file/folder"""
        is_folder = file.get('mimeType') == 'application/vnd.google-apps.folder'
        icon = ft.icons.FOLDER if is_folder else ft.icons.INSERT_DRIVE_FILE
        icon_color = ft.colors.AMBER if is_folder else ft.colors.BLUE_GREY
        
        # Format size
        size_str = ""
        if not is_folder and file.get('size'):
            size = int(file.get('size'))
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"
        
        def on_click(e):
            if is_folder:
                self.folder_stack.append(self.current_folder_id)
                self.current_path.value = f"My Drive / {file['name']}"
                self.load_files(file['id'])
        
        return ft.ListTile(
            leading=ft.Icon(icon, color=icon_color),
            title=ft.Text(file['name']),
            subtitle=ft.Text(size_str if size_str else "Folder"),
            trailing=ft.PopupMenuButton(
                icon=ft.icons.MORE_VERT,
                items=[
                    ft.PopupMenuItem(
                        text="Rename",
                        icon=ft.icons.EDIT,
                        on_click=lambda e, f=file: self.rename_file_dialog(f)
                    ),
                    ft.PopupMenuItem(
                        text="Delete",
                        icon=ft.icons.DELETE,
                        on_click=lambda e, f=file: self.delete_file_dialog(f)
                    ),
                    ft.PopupMenuItem(
                        text="Info",
                        icon=ft.icons.INFO,
                        on_click=lambda e, f=file: self.show_file_info(f)
                    ),
                ]
            ),
            on_click=on_click
        )
    
    def go_back(self, e):
        """Navigate to parent folder"""
        if self.folder_stack:
            parent_id = self.folder_stack.pop()
            self.current_path.value = "My Drive" if parent_id == 'root' else "My Drive / ..."
            self.load_files(parent_id)
    
    def handle_search(self, e):
        """Handle search query"""
        query = self.search_field.value.strip()
        if not query:
            self.load_files()
            return
        
        self.status_bar.value = f"Searching for '{query}'..."
        self.update()
        
        files = self.drive.search_files(query)
        
        self.file_list.controls.clear()
        for file in files:
            self.file_list.controls.append(self.create_file_tile(file))
        
        self.status_bar.value = f"Found {len(files)} results"
        self.update()
    
    def rename_file_dialog(self, file):
        """Show rename dialog"""
        name_field = ft.TextField(value=file['name'], autofocus=True)
        
        def rename(e):
            new_name = name_field.value.strip()
            if new_name and new_name != file['name']:
                result = self.drive.rename_file(file['id'], new_name)
                if result:
                    self.status_bar.value = f"Renamed to '{new_name}'"
                    self.load_files()
                else:
                    self.status_bar.value = "Rename failed"
                    self.update()
            dialog.open = False
            self.page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Rename File"),
            content=name_field,
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Rename", on_click=rename)
            ]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def delete_file_dialog(self, file):
        """Show delete confirmation"""
        def delete(e):
            success = self.drive.delete_file(file['id'])
            if success:
                self.status_bar.value = f"Deleted '{file['name']}'"
                self.load_files()
            else:
                self.status_bar.value = "Delete failed"
                self.update()
            dialog.open = False
            self.page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete '{file['name']}'?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Delete", on_click=delete, bgcolor=ft.colors.RED)
            ]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def show_file_info(self, file):
        """Show file information dialog"""
        info = self.drive.get_file_info(file['id'])
        if not info:
            return
        
        content = ft.Column([
            ft.Text(f"Name: {info.get('name', 'N/A')}"),
            ft.Text(f"Type: {info.get('mimeType', 'N/A')}"),
            ft.Text(f"Size: {info.get('size', 'N/A')} bytes"),
            ft.Text(f"Modified: {info.get('modifiedTime', 'N/A')}"),
        ])
        
        dialog = ft.AlertDialog(
            title=ft.Text("File Information"),
            content=content,
            actions=[ft.TextButton("Close", on_click=lambda e: self.close_dialog(dialog))]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def close_dialog(self, dialog):
        """Close a dialog"""
        dialog.open = False
        self.page.update()
    
    def handle_logout(self, e):
        """Handle logout"""
        self.auth.logout()
        self.on_logout()
    
    def build(self):
        return ft.Column([
            # Top bar
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.CLOUD, size=30, color=ft.colors.BLUE),
                    ft.Text("Drive Manager", size=20, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    self.search_field,
                    ft.IconButton(
                        icon=ft.icons.REFRESH,
                        tooltip="Refresh",
                        on_click=lambda e: self.load_files()
                    ),
                    ft.PopupMenuButton(
                        icon=ft.icons.ACCOUNT_CIRCLE,
                        tooltip=self.user_email,
                        items=[
                            ft.PopupMenuItem(
                                text="Logout",
                                icon=ft.icons.LOGOUT,
                                on_click=self.handle_logout
                            )
                        ]
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=15,
                bgcolor=ft.colors.SURFACE_VARIANT
            ),
            # Path bar
            ft.Container(
                content=self.current_path,
                padding=10,
                bgcolor=ft.colors.SURFACE_VARIANT
            ),
            # File list
            ft.Container(
                content=self.file_list,
                expand=True,
                padding=10
            ),
            # Status bar
            ft.Container(
                content=self.status_bar,
                padding=10,
                bgcolor=ft.colors.SURFACE_VARIANT
            )
        ], expand=True, spacing=0)