import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.signing import Signer, BadSignature
from documents.models import ProcessingSession

class AnalysisConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        signer = Signer()
        try:
            session_id = signer.unsign(self.session_id)
            self.session = ProcessingSession.objects.get(pk=session_id)
            self.room_group_name = f'analysis_{session_id}'

            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            await self.accept()
        except (BadSignature, ProcessingSession.DoesNotExist):
            await self.close()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        pass

    # Receive message from room group
    async def analysis_update(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))
