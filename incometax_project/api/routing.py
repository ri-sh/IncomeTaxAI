from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/analysis/(?P<session_id>.+)/$", consumers.AnalysisConsumer.as_asgi()),
]
