import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Conversation, Message
from apps.accounts.models import User

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        self.user = self.scope['user']
        
        if self.user.is_anonymous:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Mark user as online
        await self.set_user_online(True)
        
        # Send online status to all connections
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'user_id': str(self.user.id),
                'status': 'online'
            }
        )
    
    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        
        if self.user.is_authenticated:
            # Mark user as offline
            await self.set_user_online(False)
            
            # Send offline status
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status',
                    'user_id': str(self.user.id),
                    'status': 'offline'
                }
            )
    
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type', 'message')
        
        if message_type == 'message':
            content = text_data_json['content']
            
            # Save message to database
            message = await self.save_message(content)
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_id': str(message.id),
                    'message': content,
                    'sender_id': str(self.user.id),
                    'sender_name': self.user.full_name,
                    'timestamp': message.created_at.isoformat(),
                    'message_type': 'text'
                }
            )
        
        elif message_type == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'user_id': str(self.user.id),
                    'user_name': self.user.full_name,
                    'is_typing': text_data_json['is_typing']
                }
            )
        
        elif message_type == 'read_receipt':
            message_id = text_data_json['message_id']
            await self.mark_message_as_read(message_id)
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'read_receipt',
                    'message_id': message_id,
                    'user_id': str(self.user.id)
                }
            )
    
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message_id': event['message_id'],
            'content': event['message'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'timestamp': event['timestamp'],
            'message_type': event['message_type']
        }))
    
    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'user_name': event['user_name'],
            'is_typing': event['is_typing']
        }))
    
    async def user_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'status',
            'user_id': event['user_id'],
            'status': event['status']
        }))
    
    async def read_receipt(self, event):
        await self.send(text_data=json.dumps({
            'type': 'read',
            'message_id': event['message_id'],
            'user_id': event['user_id']
        }))
    
    @database_sync_to_async
    def save_message(self, content):
        conversation = Conversation.objects.get(id=self.conversation_id)
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            content=content,
            message_type='text'
        )
        # Update conversation updated_at and last_message
        conversation.last_message = message
        conversation.save()
        return message
    
    @database_sync_to_async
    def set_user_online(self, is_online):
        self.user.is_online = is_online
        self.user.save()
    
    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        try:
            from .models import MessageStatus
            message = Message.objects.get(id=message_id)
            status, created = MessageStatus.objects.get_or_create(
                message=message,
                user=self.user,
                defaults={'status': 'read'}
            )
            if not created:
                status.status = 'read'
                status.save()
        except Message.DoesNotExist:
            pass