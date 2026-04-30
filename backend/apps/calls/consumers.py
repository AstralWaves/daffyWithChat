import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import CallRecord
from apps.accounts.models import User

class WebRTCConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.call_id = self.scope['url_route']['kwargs']['call_id']
        self.room_group_name = f'call_{self.call_id}'
        self.user = self.scope['user']
        
        if self.user.is_anonymous:
            await self.close()
            return

        # Join call room
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Notify others
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user_id': str(self.user.id),
                'user_name': self.user.full_name
            }
        )
    
    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        
        if self.user.is_authenticated:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_left',
                    'user_id': str(self.user.id)
                }
            )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        event_type = data.get('type')
        
        if event_type == 'offer':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'signal_offer',
                    'offer': data['offer'],
                    'from_user_id': str(self.user.id)
                }
            )
        
        elif event_type == 'answer':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'signal_answer',
                    'answer': data['answer'],
                    'from_user_id': str(self.user.id)
                }
            )
        
        elif event_type == 'ice_candidate':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'ice_candidate',
                    'candidate': data['candidate'],
                    'from_user_id': str(self.user.id)
                }
            )
        
        elif event_type == 'toggle_video':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'video_toggle',
                    'user_id': str(self.user.id),
                    'enabled': data['enabled']
                }
            )
        
        elif event_type == 'toggle_audio':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'audio_toggle',
                    'user_id': str(self.user.id),
                    'enabled': data['enabled']
                }
            )
        
        elif event_type == 'end_call':
            await self.save_call_record(data)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'call_ended',
                    'user_id': str(self.user.id)
                }
            )

    async def signal_offer(self, event):
        if event['from_user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'offer',
                'offer': event['offer'],
                'from_user_id': event['from_user_id']
            }))

    async def signal_answer(self, event):
        if event['from_user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'answer',
                'answer': event['answer'],
                'from_user_id': event['from_user_id']
            }))

    async def ice_candidate(self, event):
        if event['from_user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'ice_candidate',
                'candidate': event['candidate'],
                'from_user_id': event['from_user_id']
            }))

    async def user_joined(self, event):
        await self.send(text_data=json.dumps(event))

    async def user_left(self, event):
        await self.send(text_data=json.dumps(event))

    async def video_toggle(self, event):
        await self.send(text_data=json.dumps(event))

    async def audio_toggle(self, event):
        await self.send(text_data=json.dumps(event))

    async def call_ended(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def save_call_record(self, data):
        try:
            CallRecord.objects.create(
                caller=self.user,
                callee_id=data.get('callee_id'),
                call_type=data.get('call_type', 'video'),
                duration=data.get('duration', 0),
                status='completed'
            )
        except Exception:
            pass