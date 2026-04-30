import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from apps.chat.middleware import JWTAuthMiddleware
from apps.chat.routing import websocket_urlpatterns as chat_urls
from apps.calls.routing import websocket_urlpatterns as call_urls

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daffy_project.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JWTAuthMiddleware(
        AuthMiddlewareStack(
            URLRouter(
                chat_urls + call_urls
            )
        )
    ),
})