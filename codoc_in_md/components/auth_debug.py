"""Temporary auth debug page. Remove after debugging."""

import reflex as rx

try:
    from reflex_ddns_auth import AuthState
    from reflex_ddns_auth.state import DDNS_AUTH_SECRET, DDNS_AUTH_COOKIE
    _HAS_AUTH = True
except ImportError:
    _HAS_AUTH = False
    DDNS_AUTH_SECRET = ""
    DDNS_AUTH_COOKIE = ""


class AuthDebugState(rx.State):
    cookie_header_raw: str = ""
    ddns_token_found: bool = False
    ddns_token_preview: str = ""
    secret_set: bool = False
    secret_length: int = 0
    cookie_name: str = ""
    debug_loaded: bool = False

    @rx.event
    async def load_debug(self):
        if self.debug_loaded:
            return
        self.debug_loaded = True
        self.cookie_name = DDNS_AUTH_COOKIE or "(not configured)"
        self.secret_set = bool(DDNS_AUTH_SECRET)
        self.secret_length = len(DDNS_AUTH_SECRET)

        cookie_header = self.router.headers.cookie
        if cookie_header:
            names = []
            for part in cookie_header.split(";"):
                part = part.strip()
                if "=" in part:
                    names.append(part.split("=")[0].strip())
            self.cookie_header_raw = f"Cookie names found: {', '.join(names)}"
        else:
            self.cookie_header_raw = "(no cookie header)"

        from http.cookies import SimpleCookie
        try:
            cookies = SimpleCookie(cookie_header)
            morsel = cookies.get(DDNS_AUTH_COOKIE)
            if morsel:
                self.ddns_token_found = True
                val = morsel.value
                self.ddns_token_preview = f"{val[:20]}...{val[-10:]}" if len(val) > 35 else val
            else:
                self.ddns_token_found = False
                self.ddns_token_preview = "(not found)"
        except Exception as e:
            self.ddns_token_preview = f"Error: {e}"


def auth_debug_page() -> rx.Component:
    """Temporary debug page for auth troubleshooting."""
    rows = [
        ("reflex_ddns_auth installed", "Yes" if _HAS_AUTH else "No"),
    ]

    return rx.el.main(
        rx.el.div(
            rx.el.h1("Auth Debug", class_name="text-2xl font-bold mb-6"),
            rx.el.div(
                rx.el.h2("Environment", class_name="text-lg font-semibold mb-2"),
                rx.el.div(
                    _row("reflex_ddns_auth installed", "Yes" if _HAS_AUTH else "No"),
                    _row_var("DDNS_AUTH_COOKIE name", AuthDebugState.cookie_name),
                    _row_var("DDNS_AUTH_SECRET set", AuthDebugState.secret_set.to(str)),
                    _row_var("DDNS_AUTH_SECRET length", AuthDebugState.secret_length.to(str)),
                    class_name="space-y-1 mb-6",
                ),
                rx.el.h2("Cookie Header", class_name="text-lg font-semibold mb-2"),
                rx.el.div(
                    _row_var("Raw cookie info", AuthDebugState.cookie_header_raw),
                    _row_var("ddns_auth token found", AuthDebugState.ddns_token_found.to(str)),
                    _row_var("Token preview", AuthDebugState.ddns_token_preview),
                    class_name="space-y-1 mb-6",
                ),
                *(
                    [
                        rx.el.h2("AuthState", class_name="text-lg font-semibold mb-2"),
                        rx.el.div(
                            _row_var("auth_status", AuthState.auth_status),
                            _row_var("is_logged_in", AuthState.is_logged_in.to(str)),
                            _row_var("user_email", AuthState.user_email),
                            _row_var("user_name", AuthState.user_name),
                            _row_var("user_avatar", AuthState.user_avatar),
                            class_name="space-y-1 mb-6",
                        ),
                        rx.el.h2("Actions", class_name="text-lg font-semibold mb-2"),
                        rx.el.div(
                            rx.el.a(
                                "Login via Relack",
                                href=AuthState.login_url,
                                class_name="text-violet-600 underline mr-4",
                            ),
                            rx.el.a(
                                "Logout",
                                href=AuthState.logout_url,
                                class_name="text-red-600 underline",
                            ),
                        ),
                    ] if _HAS_AUTH else [
                        rx.el.p("AuthState not available (import failed)",
                                class_name="text-red-500"),
                    ]
                ),
                class_name="max-w-2xl",
            ),
            class_name="p-8",
        ),
    )


def _row(label: str, value: str) -> rx.Component:
    return rx.el.div(
        rx.el.span(f"{label}: ", class_name="font-medium text-gray-600"),
        rx.el.span(value, class_name="font-mono text-gray-900"),
        class_name="text-sm",
    )


def _row_var(label: str, value) -> rx.Component:
    return rx.el.div(
        rx.el.span(f"{label}: ", class_name="font-medium text-gray-600"),
        rx.el.span(value, class_name="font-mono text-gray-900"),
        class_name="text-sm",
    )
