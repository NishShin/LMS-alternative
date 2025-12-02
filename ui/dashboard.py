# dashboard.py
import flet as ft
from services.drive_service import DriveService
import re
import json
import os
from ui.custom_control.custom_controls import ButtonWithMenu

FAVORITES_FILE = "favorites.json"


class Dashboard:
    """Main dashboard view with sidebar, folder listing, link paste & favorites"""

    def __init__(self, page, auth_service, on_logout):
        self.page = page
        self.auth = auth_service
        self.on_logout = on_logout
        self.drive = DriveService(auth_service.get_service())

        self.current_folder_id = "root"
        self.current_folder_name = "My Drive"
        self.folder_stack = []  # (folder_id, folder_name)
        self.selected_files = set()
        self.current_view = "your_folders"  # your_folders | shared_drives | folder_detail

        # user info
        user_info = self.auth.get_user_info()
        self.user_email = user_info.get("emailAddress", "User") if user_info else "User"

        # UI controls
        self.search_field = ft.TextField(
            hint_text="Search",
            prefix_icon=ft.Icons.SEARCH,
            on_submit=self.handle_search,
            border_color=ft.Colors.GREY_400,
            filled=True,
            expand=True,
        )

        # Input for paste link (top of sidebar)
        self.paste_link_field = ft.TextField(
            hint_text="Paste shared folder link and press Enter",
            on_submit=self.handle_paste_link,
            expand=True,
        )

        # Favorites (loaded from JSON)
        self.favorites = self.load_favorites()

        # Folder list column (main content)
        self.folder_list = ft.Column(spacing=0, scroll=ft.ScrollMode.ALWAYS, expand=True)
        self.main_view_container = None

        # Build the UI and load initial folders
        self.page.title = "Drive Manager"
        self.page.vertical_alignment = ft.MainAxisAlignment.START
        self.page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH

        self.load_your_folders()

    # -------------------------
    # Favorites (simple JSON)
    # -------------------------
    def load_favorites(self):
        if os.path.exists(FAVORITES_FILE):
            try:
                with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print("Error loading favorites:", e)
        # default structure
        return {}

    def save_favorites(self):
        try:
            with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
                json.dump(self.favorites, f, indent=2)
        except Exception as e:
            print("Error saving favorites:", e)

    def add_favorite(self, subject, folder_id, folder_name):
        self.favorites.setdefault(subject, [])
        # avoid duplicates
        if any(f["id"] == folder_id for f in self.favorites[subject]):
            return False
        self.favorites[subject].append({"id": folder_id, "name": folder_name})
        self.save_favorites()
        return True

    def remove_favorite(self, subject, folder_id):
        if subject not in self.favorites:
            return False
        self.favorites[subject] = [f for f in self.favorites[subject] if f["id"] != folder_id]
        if len(self.favorites[subject]) == 0:
            del self.favorites[subject]
        self.save_favorites()
        return True

    # -------------------------
    # Link utilities
    # -------------------------
    def extract_id_from_link(self, link):
        """Extract folder ID from common Drive folder link formats"""
        # common patterns:
        # https://drive.google.com/drive/folders/<id>
        # https://drive.google.com/open?id=<id>
        # https://drive.google.com/drive/u/0/folders/<id>
        if not link or not isinstance(link, str):
            return None
        # try folders path
        m = re.search(r"/folders/([a-zA-Z0-9_-]+)", link)
        if m:
            return m.group(1)
        # try open?id=
        m = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", link)
        if m:
            return m.group(1)
        return None

    # -------------------------
    # Loading views
    # -------------------------
    def load_your_folders(self):
        """Load user's root folders (My Drive root)"""
        self.current_view = "your_folders"
        self.current_folder_id = "root"
        self.current_folder_name = "My Drive"
        self.folder_stack = []
        self.folder_list.controls.clear()

        try:
            result = self.drive.list_files("root", page_size=100)
            files = result.get("files", [])
            folders = [f for f in files if f.get("mimeType") == "application/vnd.google-apps.folder"]

            if not folders:
                self.folder_list.controls.append(
                    ft.Container(
                        content=ft.Text("No folders found", color=ft.Colors.GREY_500), padding=20
                    )
                )
            else:
                for folder in folders:
                    # count subfolders
                    sub_result = self.drive.list_files(folder["id"], page_size=100)
                    sub_count = len([f for f in sub_result.get("files", []) if f.get("mimeType") == "application/vnd.google-apps.folder"])
                    self.folder_list.controls.append(self.create_folder_item(folder, sub_count))

        except Exception as e:
            print("Error loading your folders:", e)
            self.folder_list.controls.append(
                ft.Container(content=ft.Text("Error loading folders", color=ft.Colors.RED), padding=20)
            )

        self.page.update()

    def load_shared_drives(self):
        """Load shared drives (Team drives)"""
        self.current_view = "shared_drives"
        self.folder_stack = []
        self.folder_list.controls.clear()

        try:
            results = self.drive.service.drives().list(pageSize=100, fields="drives(id, name)").execute()
            shared_drives = results.get("drives", [])

            if not shared_drives:
                self.folder_list.controls.append(ft.Container(content=ft.Text("No shared drives found", color=ft.Colors.GREY_500), padding=20))
            else:
                for d in shared_drives:
                    # show as folder item; clicking will open it
                    fake_folder = {"id": d["id"], "name": d["name"], "mimeType": "application/vnd.google-apps.folder"}
                    self.folder_list.controls.append(self.create_folder_item(fake_folder, 0, is_shared_drive=True))
        except Exception as e:
            print("Error loading shared drives:", e)
            self.folder_list.controls.append(ft.Container(content=ft.Text("Error loading shared drives", color=ft.Colors.RED), padding=20))

        self.page.update()

    # -------------------------
    # Folder / File views
    # -------------------------
    def show_folder_contents(self, folder_id, folder_name=None, is_shared_drive=False):
        """Show detailed files/folders inside a folder_id"""
        self.current_view = "folder_detail"
        if folder_name:
            display_name = folder_name
        else:
            # try to fetch info for name
            info = self.drive.get_file_info(folder_id)
            display_name = info.get("name") if info else folder_id

        # push current for back
        self.folder_stack.append((self.current_folder_id, self.current_folder_name))
        self.current_folder_id = folder_id
        self.current_folder_name = display_name

        # rebuild folder_list
        self.folder_list.controls.clear()

        # Back button + title
        back_btn = ft.Row(
            [
                ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: self.go_back()),
                ft.Text(display_name, size=18, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [
                        ft.ElevatedButton("Save to favorites", on_click=lambda e: self.open_save_favorite_dialog()),
                        ft.ElevatedButton("Refresh", on_click=lambda e: self.refresh_folder_contents()),
                    ],
                    spacing=8,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        self.folder_list.controls.append(back_btn)

        # Get folder contents
        try:
            result = self.drive.list_files(folder_id, page_size=200)
            files = result.get("files", [])
            if not files:
                self.folder_list.controls.append(ft.Container(content=ft.Text("Folder is empty", color=ft.Colors.GREY_500), padding=20))
            else:
                for f in files:
                    self.folder_list.controls.append(self.create_file_item(f))
        except Exception as e:
            print("Error listing folder contents:", e)
            self.folder_list.controls.append(ft.Container(content=ft.Text("Error loading contents", color=ft.Colors.RED), padding=20))

        self.page.update()

    def refresh_folder_contents(self):
        # re-open current folder
        self.show_folder_contents(self.current_folder_id, self.current_folder_name)

    def go_back(self):
        if not self.folder_stack:
            # go back to your folders view
            self.load_your_folders()
            return
        fid, fname = self.folder_stack.pop()
        self.current_folder_id = fid
        self.current_folder_name = fname
        if fid == "root":
            self.load_your_folders()
        else:
            self.show_folder_contents(fid, fname)

    # -------------------------
    # UI Item creators
    # -------------------------
    def create_folder_item(self, folder, subfolder_count, is_shared_drive=False):
        folder_name = folder.get("name", "Untitled")
        display_name = folder_name if len(folder_name) < 40 else folder_name[:37] + "..."

        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.FOLDER, size=24),
                    ft.Column(
                        [
                            ft.Text(display_name, size=14, weight=ft.FontWeight.W_500),
                            ft.Text(f"{subfolder_count} folders" if subfolder_count is not None else "", size=12, color=ft.Colors.GREY_600),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.IconButton(icon=ft.Icons.MORE_VERT, on_click=lambda e, f=folder: self.show_folder_menu(f, is_shared_drive)),
                ],
            ),
            padding=ft.padding.symmetric(horizontal=15, vertical=12),
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.GREY_300)),
            bgcolor=ft.Colors.WHITE,
            on_click=lambda e, f=folder: self.open_folder(f, is_shared_drive),
        )

    def create_file_item(self, file):
        is_folder = file.get("mimeType") == "application/vnd.google-apps.folder"
        icon = ft.Icons.FOLDER if is_folder else ft.Icons.INSERT_DRIVE_FILE
        size_str = "Folder" if is_folder else self.format_size(file.get("size"))

        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icon, size=24),
                    ft.Column(
                        [
                            ft.Text(file.get("name", "Untitled"), size=14, weight=ft.FontWeight.W_500),
                            ft.Text(size_str, size=12, color=ft.Colors.GREY_600),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.IconButton(icon=ft.Icons.MORE_VERT, on_click=lambda e, f=file: self.show_file_menu(f)),
                ]
            ),
            padding=ft.padding.symmetric(horizontal=15, vertical=10),
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.GREY_200)),
            on_click=lambda e, f=file: self.handle_file_click(f) if is_folder else None,
        )

    def format_size(self, size):
        try:
            if not size:
                return "Unknown size"
            s = int(size)
            if s < 1024:
                return f"{s} B"
            if s < 1024 * 1024:
                return f"{s / 1024:.1f} KB"
            if s < 1024 * 1024 * 1024:
                return f"{s / (1024 * 1024):.1f} MB"
            return f"{s / (1024 * 1024 * 1024):.1f} GB"
        except:
            return "Unknown size"

    # -------------------------
    # Actions
    # -------------------------
    def open_folder(self, folder, is_shared_drive=False):
        self.show_folder_contents(folder["id"], folder.get("name", folder["id"]), is_shared_drive)

    def handle_file_click(self, file):
        if file.get("mimeType") == "application/vnd.google-apps.folder":
            self.show_folder_contents(file["id"], file["name"])
        else:
            # show file info
            self.show_file_info(file)

    def show_folder_menu(self, folder, is_shared_drive=False):
        # Placeholder: in future, add options (open, save favorite, copy link)
        self.open_folder(folder, is_shared_drive)

    def show_file_menu(self, file):
        # pop menu: Rename, Delete, Info
        def on_rename(e):
            self.rename_file_dialog(file)
            popup.open = False
            self.page.update()

        def on_delete(e):
            self.delete_file_dialog(file)
            popup.open = False
            self.page.update()

        def on_info(e):
            self.show_file_info(file)
            popup.open = False
            self.page.update()

        popup = ft.PopupMenuButton(
            items=[
                ft.PopupMenuItem(text="Info", on_click=on_info),
                ft.PopupMenuItem(text="Rename", on_click=on_rename),
                ft.PopupMenuItem(text="Delete", on_click=on_delete),
            ]
        )
        # open the popup (adds to page)
        self.page.add(popup)
        popup.open = True
        self.page.update()

    # -------------------------
    # Create / Upload
    # -------------------------
    def show_new_menu(self, e):
        popup = ft.PopupMenuButton(
            items=[
                ft.PopupMenuItem(
                    text="New Folder",
                    on_click=lambda e: self.create_new_folder_dialog()
                ),
                ft.PopupMenuItem(
                    text="Upload File",
                    on_click=lambda e: self.select_file_to_upload()
                ),
            ]
        )
        self.page.add(popup)
        popup.open = True
        self.page.update()



    def create_new_folder_dialog(self):
        name_field = ft.TextField(label="Folder name", autofocus=True)

        def create(e):
            folder_name = name_field.value.strip()
            if folder_name:
                folder = self.drive.create_folder(folder_name, parent_id=self.current_folder_id)
                if folder:
                    print("Created folder:", folder)
                    self.refresh_folder_contents()
                else:
                    print("Failed to create folder")
            # remove overlay
            self.page.overlay.pop()
            self.page.update()

        dialog_container = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Create New Folder"),
                    name_field,
                    ft.Row(
                        [
                            ft.TextButton("Cancel", on_click=lambda e: self.page.overlay.pop()),
                            ft.ElevatedButton("Create", on_click=create),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                        spacing=10,
                    )
                ],
                spacing=10,
            ),
            padding=20,
            bgcolor=ft.Colors.WHITE,
            border_radius=10,
            width=300,
            height=150,
        )

        self.page.overlay.append(dialog_container)
        self.page.update()




    def select_file_to_upload(self):
        # Use Flet FilePicker
        def on_result(e: ft.FilePickerResultEvent):
            # e.files is list of FilePickerResult
            if not e.files:
                return
            for f in e.files:
                # f.path is local path
                uploaded = self.drive.upload_file(f.path, parent_id=self.current_folder_id)
                print("Uploaded:", uploaded)
            self.refresh_folder_contents()

        file_picker = ft.FilePicker(on_result=on_result)
        # attach to page overlay and open
        self.page.overlay.append(file_picker)
        self.page.update()
        file_picker.pick_files()

    # -------------------------
    # Rename / Delete / Info
    # -------------------------
    def rename_file_dialog(self, file):
        name_field = ft.TextField(value=file["name"], autofocus=True)

        def rename(e):
            new_name = name_field.value.strip()
            if new_name and new_name != file["name"]:
                result = self.drive.rename_file(file["id"], new_name)
                if result:
                    self.refresh_folder_contents()
            dialog.open = False
            self.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Rename"),
            content=name_field,
            actions=[ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)), ft.ElevatedButton("Rename", on_click=rename)],
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def delete_file_dialog(self, file):
        def delete(e):
            success = self.drive.delete_file(file["id"])
            if success:
                self.refresh_folder_contents()
            dialog.open = False
            self.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete '{file.get('name', '')}'?"),
            actions=[ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)), ft.ElevatedButton("Delete", on_click=delete, bgcolor=ft.Colors.RED)],
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def show_file_info(self, file):
        info = self.drive.get_file_info(file["id"])
        if not info:
            return
        content = ft.Column(
            [
                ft.Text(f"Name: {info.get('name', 'N/A')}"),
                ft.Text(f"Type: {info.get('mimeType', 'N/A')}"),
                ft.Text(f"Size: {info.get('size', 'N/A')} bytes"),
                ft.Text(f"Modified: {info.get('modifiedTime', 'N/A')}"),
                ft.TextButton("Open in Drive", on_click=lambda e: self.page.launch(info.get("webViewLink", "#"))),
            ]
        )
        dialog = ft.AlertDialog(title=ft.Text("File Information"), content=content, actions=[ft.TextButton("Close", on_click=lambda e: self.close_dialog(dialog))])
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    # -------------------------
    # Search & Paste link
    # -------------------------
    def handle_search(self, e):
        query = self.search_field.value.strip()
        if not query:
            self.load_your_folders()
            return
        # search across drive root (or consider using Drive API search)
        results = self.drive.search_files(query)
        self.folder_list.controls.clear()
        if not results:
            self.folder_list.controls.append(ft.Container(content=ft.Text("No results", color=ft.Colors.GREY_500), padding=20))
        else:
            for r in results:
                # show either folder or file results
                if r.get("mimeType") == "application/vnd.google-apps.folder":
                    self.folder_list.controls.append(self.create_folder_item(r, 0))
                else:
                    self.folder_list.controls.append(self.create_file_item(r))
        self.page.update()

    def paste_link_dialog(self, e):
        link_field = ft.TextField(hint_text="Paste Google Drive folder link", autofocus=True)

        def open_folder(e):
            link = link_field.value.strip()
            folder_id = self.extract_id_from_link(link)
            if folder_id:
                self.show_folder_contents(folder_id, "Shared Folder")
            else:
                self.page.snack_bar = ft.SnackBar(ft.Text("Invalid Drive link"))
                self.page.snack_bar.open = True
            dialog.open = False
            self.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Open Shared Folder"),
            content=link_field,
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Open", on_click=open_folder)
            ]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()


    def handle_paste_link(self, e):
        link = e.control.value.strip()
        if not link:
            return
        folder_id = self.extract_id_from_link(link)
        if not folder_id:
            self.page.snack_bar = ft.SnackBar(ft.Text("Invalid link format"))
            self.page.snack_bar.open = True
            self.page.update()
            return
        # Open folder and allow saving to favorites
        self.show_folder_contents(folder_id, "Shared Folder")
        # clear input
        self.paste_link_field.value = ""
        self.page.update()

    def open_save_favorite_dialog(self):
        # ask subject name
        subject_field = ft.TextField(label="Subject / Category (e.g. Math 11)", autofocus=True)

        def save(e):
            subject = subject_field.value.strip()
            if not subject:
                return
            added = self.add_favorite(subject, self.current_folder_id, self.current_folder_name)
            if added:
                self.page.snack_bar = ft.SnackBar(ft.Text("Saved to favorites"))
                self.page.snack_bar.open = True
            else:
                self.page.snack_bar = ft.SnackBar(ft.Text("Already in favorites"))
                self.page.snack_bar.open = True
            dialog.open = False
            self.page.update()

        dialog = ft.AlertDialog(title=ft.Text("Save folder to favorites"), content=subject_field, actions=[ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)), ft.ElevatedButton("Save", on_click=save)])
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    # -------------------------
    # Dialog helpers
    # -------------------------
    def close_dialog(self, dialog):
        dialog.open = False
        self.page.update()

    # -------------------------
    # Build & return the main view
    # -------------------------
    def build_favorites_ui(self):
        """Build a column showing saved subjects and their folders"""
        col = ft.Column(spacing=6)
        if not self.favorites:
            col.controls.append(ft.Text("No saved links", color=ft.Colors.GREY_600))
            return col

        for subject, folders in self.favorites.items():
            # subject header row
            subject_row = ft.Row(
                [
                    ft.Text(subject, weight=ft.FontWeight.BOLD),
                    ft.IconButton(icon=ft.Icons.DELETE, tooltip="Remove subject", on_click=lambda e, s=subject: self.remove_subject_confirm(s)),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
            col.controls.append(subject_row)

            for f in folders:
                # each saved folder: name, open, delete
                folder_row = ft.Row(
                    [
                        ft.Text(f.get("name", f.get("id")), size=13, expand=True),
                        ft.IconButton(icon=ft.Icons.OPEN_IN_NEW, on_click=lambda e, fid=f["id"], nm=f.get("name", ""): self.show_folder_contents(fid, nm)),
                        ft.IconButton(icon=ft.Icons.DELETE, on_click=lambda e, s=subject, fid=f["id"]: self.confirm_remove_favorite(s, fid)),
                    ]
                )
                col.controls.append(folder_row)

        return col

    def remove_subject_confirm(self, subject):
        def remove(e):
            if subject in self.favorites:
                del self.favorites[subject]
                self.save_favorites()
            dialog.open = False
            self.page.update()
        dialog = ft.AlertDialog(title=ft.Text("Remove subject"), content=ft.Text(f"Remove all favorites under '{subject}'?"), actions=[ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)), ft.ElevatedButton("Remove", on_click=remove, bgcolor=ft.Colors.RED)])
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def confirm_remove_favorite(self, subject, folder_id):
        def remove(e):
            self.remove_favorite(subject, folder_id)
            dialog.open = False
            self.page.update()
        dialog = ft.AlertDialog(title=ft.Text("Remove favorite"), content=ft.Text("Remove this saved folder?"), actions=[ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)), ft.ElevatedButton("Remove", on_click=remove, bgcolor=ft.Colors.RED)])
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def handle_logout(self, e):
        self.auth.logout()
        self.on_logout()


    def handle_action(self, selected_item):
        print(f"User selected: {selected_item}")
        print("HANDLE_ACTION CALLED with:", selected_item)
        print("PAGE in handle_action =", self.page)
        self.page.snack_bar = ft.SnackBar(ft.Text(f"Selected: {selected_item}"))

        if selected_item == "Create Folder":
            
            self.create_new_folder_dialog()
            print("Create Folder")
        elif selected_item == "Upload File":
            print("Upload File")
            self.select_file_to_upload()
        
        self.page.snack_bar.open = True
        self.page.update()


    def get_view(self):
    # ---- LEFT SIDEBAR ----
        sidebar = ft.Container(
            width=260,
            bgcolor=ft.Colors.GREY_100,
            padding=20,
            content=ft.Column(
                controls=[
                    ButtonWithMenu(
                        text="+ NEW",
                        menu_items=[ "Create Folder", "Upload File"],
                        on_menu_select= self.handle_action,
                        # on_click=self.show_new_menu,
                        page=self.page
                    ),

                    ft.Container(height=20),
                    ft.ElevatedButton(
                        "SETTINGS",
                        on_click=lambda e: None,
                        style=ft.ButtonStyle(
                            padding=20,
                            bgcolor=ft.Colors.WHITE,
                            color=ft.Colors.BLACK,
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                    ),
                    ft.ElevatedButton(
                        "TO-DO",
                        on_click=lambda e: None,
                        style=ft.ButtonStyle(
                            padding=20,
                            bgcolor=ft.Colors.WHITE,
                            color=ft.Colors.BLACK,
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                    ),
                    ft.ElevatedButton(
                        "ACCOUNT",
                        on_click=self.handle_logout,
                        style=ft.ButtonStyle(
                            padding=20,
                            bgcolor=ft.Colors.WHITE,
                            color=ft.Colors.BLACK,
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                    ),
                ],
                spacing=15,
            ),
        )

        # ---- TOP BAR ----
        top_bar = ft.Container(
            bgcolor=ft.Colors.WHITE,
            padding=20,
            content=ft.Row(
                [
                    self.search_field,
                    ft.IconButton(
                        icon=ft.Icons.ACCOUNT_CIRCLE,
                        icon_size=36,
                        tooltip=self.user_email,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
        )

        # ---- TABS ----
        tabs = ft.Container(
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            content=ft.Row(
                [
                    ft.TextButton(
                        "YOUR FOLDERS",
                        on_click=lambda e: self.load_your_folders(),
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.WHITE,
                            color=ft.Colors.BLACK,
                            shape=ft.RoundedRectangleBorder(radius=12),
                            padding=15
                        )
                    ),
                    ft.TextButton(
                        "Pasted Links",
                        on_click=lambda e: print("Pasted Links clicked"),
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.WHITE,
                            color=ft.Colors.BLACK,
                            shape=ft.RoundedRectangleBorder(radius=12),
                            padding=15
                        )
                    ),
                    ft.TextButton(
                        "Your Drive",
                        on_click=lambda e: self.load_your_folders(),
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.WHITE,
                            color=ft.Colors.BLACK,
                            shape=ft.RoundedRectangleBorder(radius=12),
                            padding=15
                        )
                    ),
                ],
                spacing=10,
            ),
        )

        # ---- MAIN CONTENT ----
        main_content = ft.Column(
            controls=[
                top_bar,
                tabs,
                ft.Container(
                    bgcolor=ft.Colors.WHITE,
                    padding=0,
                    expand=True,
                    content=self.folder_list,
                ),
            ],
            expand=True,
            spacing=0,
        )

        # ---- FULL PAGE LAYOUT ----
        return ft.Row(
            [
                sidebar,
                ft.VerticalDivider(width=1, color=ft.Colors.GREY_300),
                main_content,
            ],
            expand=True,
        )
