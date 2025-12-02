import flet as ft

class ButtonWithMenu(ft.PopupMenuButton):
    """Custom PopupMenuButton styled to look like an ElevatedButton"""
    
    def __init__(self, text, menu_items, on_menu_select=None, page=None, **kwargs):
        self.page = page  # <-- IMPORTANT FIX

        popup_items = [
            ft.PopupMenuItem(text=item, on_click=self._handle_menu_click)
            for item in menu_items
        ]
        
        self.button_content = ft.Container(
            content=ft.Row(
                [
                    ft.Text(text, size=14, weight=ft.FontWeight.W_500, color=ft.Colors.ON_PRIMARY),
                    ft.Icon(ft.Icons.ARROW_DROP_DOWN, size=18, color=ft.Colors.ON_PRIMARY),
                ],
                spacing=8,
                alignment=ft.MainAxisAlignment.CENTER,
                tight=True,
            ),
            bgcolor=ft.Colors.PRIMARY,
            padding=ft.padding.symmetric(horizontal=24, vertical=10),
            border_radius=20,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=2,
                color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
                offset=ft.Offset(0, 1),
            ),
            animate=ft.Animation(100, ft.AnimationCurve.EASE_IN_OUT),
            on_hover=self._on_hover,
        )
        
        super().__init__(
            content=self.button_content,
            items=popup_items,
            **kwargs
        )
        
        self.on_menu_select = on_menu_select
    
    def _on_hover(self, e):
        if e.data == "true":
            self.button_content.shadow = ft.BoxShadow(
                spread_radius=0,
                blur_radius=8,
                color=ft.Colors.with_opacity(0.4, ft.Colors.BLACK),
                offset=ft.Offset(0, 2),
            )
            self.button_content.scale = 1.02
        else:
            self.button_content.shadow = ft.BoxShadow(
                spread_radius=0,
                blur_radius=2,
                color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
                offset=ft.Offset(0, 1),
            )
            self.button_content.scale = 1.0
        
        self.button_content.update()
    
    def _handle_menu_click(self, e):
        print("MENU CLICKED:", e.control.text)
        print("CALLING on_menu_select:", self.on_menu_select)
        if self.on_menu_select:
            self.on_menu_select(e.control.text)
