from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/logistics/$', consumers.LogisticsConsumer.as_asgi()),
    re_path(r'ws/agriculture/$', consumers.AgricultureConsumer.as_asgi()),
]
