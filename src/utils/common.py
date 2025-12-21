import flet as ft
import json
import os
from pathlib import Path
from datetime import datetime, timedelta


def load_json_file(filepath, default=None):
    if isinstance(filepath, str):
        filepath = Path(filepath)
    if filepath.exists():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return default if default is not None else []


def save_json_file(filepath, data):
    if isinstance(filepath, str):
        filepath = Path(filepath)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving: {e}")
        return False


def format_file_size(size_bytes):
    if size_bytes is None:
        return "Unknown size"
    try:
        size = int(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    except (ValueError, TypeError):
        return "Unknown size"


def parse_mime_type(mime_type):
    mime_map = {
        'application/vnd.google-apps.folder': ('folder', 'folder'),
        'application/pdf': ('document', 'picture_as_pdf'),
        'application/msword': ('document', 'description'),
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ('document', 'description'),
        'application/vnd.ms-excel': ('spreadsheet', 'table_chart'),
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ('spreadsheet', 'table_chart'),
        'application/vnd.ms-powerpoint': ('presentation', 'slideshow'),
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': ('presentation', 'slideshow'),
    }
    
    if mime_type in mime_map:
        return {'category': mime_map[mime_type][0], 'icon': mime_map[mime_type][1]}
    elif mime_type and mime_type.startswith('image/'):
        return {'category': 'image', 'icon': 'image'}
    elif mime_type and mime_type.startswith('video/'):
        return {'category': 'video', 'icon': 'video_file'}
    elif mime_type and mime_type.startswith('audio/'):
        return {'category': 'audio', 'icon': 'audio_file'}
    elif mime_type and mime_type.startswith('text/'):
        return {'category': 'document', 'icon': 'description'}
    else:
        return {'category': 'file', 'icon': 'insert_drive_file'}


def extract_drive_id(url):
    import re
    patterns = [
        r"/folders/([a-zA-Z0-9_-]+)",
        r"/file/d/([a-zA-Z0-9_-]+)",
        r"[?&]id=([a-zA-Z0-9_-]+)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    if len(url) > 20 and "/" not in url:
        return url
    
    return None


def open_url(url):
    import webbrowser
    webbrowser.open(url)


def open_drive_file(file_id):
    open_url(f"https://drive.google.com/file/d/{file_id}/view")


def open_drive_folder(folder_id):
    open_url(f"https://drive.google.com/drive/folders/{folder_id}")


def show_snackbar(page, message, color=ft.Colors.BLUE):
    page.snack_bar = ft.SnackBar(content=ft.Text(message), bgcolor=color)
    page.snack_bar.open = True
    page.update()


def create_dialog(page, title, content, actions=None):
    dialog = ft.AlertDialog(
        title=ft.Text(title),
        content=content,
        actions=actions or [ft.TextButton("OK", on_click=lambda e: close_dialog(dialog, page))]
    )
    page.dialog = dialog
    dialog.open = True
    page.update()
    return dialog


def close_dialog(dialog, page):
    dialog.open = False
    page.update()


def create_overlay(page, content, title=None, width=400, height=None):
    def close_overlay(e):
        if overlay in page.overlay:
            page.overlay.remove(overlay)
            page.update()
    
    header_controls = []
    if title:
        header_controls.append(
            ft.Text(title, size=20, weight=ft.FontWeight.BOLD, 
                   overflow=ft.TextOverflow.VISIBLE, no_wrap=False, expand=True)
        )
    header_controls.append(ft.IconButton(icon=ft.Icons.CLOSE, on_click=close_overlay))
    
    overlay_content = ft.Column([
        ft.Row(header_controls, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Divider(),
        content
    ], tight=True, spacing=10)
    
    overlay = ft.Container(
        content=ft.Container(
            content=overlay_content,
            padding=20,
            bgcolor=ft.Colors.WHITE,
            border_radius=10,
            width=width,
            height=height,
            shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK))
        ),
        alignment=ft.alignment.center,
        expand=True,
        bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
        on_click=lambda e: None
    )
    
    page.overlay.append(overlay)
    page.update()
    return overlay, close_overlay


def calculate_time_difference(start_dt, end_dt):
    if not start_dt or not end_dt:
        return None, "No timing data"
    
    try:
        if isinstance(start_dt, str):
            start_dt = datetime.fromisoformat(start_dt) if 'T' in start_dt else datetime.strptime(start_dt, '%Y-%m-%d %H:%M')
        if isinstance(end_dt, str):
            end_dt = datetime.fromisoformat(end_dt)
        
        diff = end_dt - start_dt
        
        if diff.total_seconds() > 0:
            days = diff.days
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            
            if days > 0:
                return "early", f"✅ {days}d {hours}h early"
            elif hours > 0:
                return "early", f"✅ {hours}h {minutes}m early"
            else:
                return "early", f"✅ {minutes}m early"
        else:
            diff = abs(diff)
            days = diff.days
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            
            if days > 0:
                return "late", f"⚠️ {days}d {hours}h late"
            elif hours > 0:
                return "late", f"⚠️ {hours}h {minutes}m late"
            else:
                return "late", f"⚠️ {minutes}m late"
    except:
        return None, "Invalid timing data"


def get_time_remaining(deadline_str):
    if not deadline_str:
        return "No deadline"
    try:
        deadline = datetime.fromisoformat(deadline_str)
        now = datetime.now()
        remaining = deadline - now
        
        if remaining.total_seconds() <= 0:
            return "Overdue"
        
        days = remaining.days
        hours = remaining.seconds // 3600
        
        if days > 0:
            return f"⏱️ {days}d {hours}h remaining"
        elif hours > 0:
            minutes = (remaining.seconds % 3600) // 60
            return f"⏱️ {hours}h {minutes}m remaining"
        else:
            minutes = remaining.seconds // 60
            return f"⏱️ {minutes}m remaining"
    except:
        return "Invalid deadline"


def validate_email(email):
    if not email:
        return False, "Email is required"
    if "@" not in email or "." not in email:
        return False, "Invalid email format"
    return True, ""


def create_icon_button(icon, tooltip, on_click, color=None):
    return ft.IconButton(
        icon=icon,
        tooltip=tooltip,
        on_click=on_click,
        icon_color=color
    )


def create_list_tile(leading_icon, title, subtitle=None, on_click=None, trailing=None):
    return ft.ListTile(
        leading=ft.Icon(leading_icon),
        title=ft.Text(title),
        subtitle=ft.Text(subtitle) if subtitle else None,
        on_click=on_click,
        trailing=trailing
    )