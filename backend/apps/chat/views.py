from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from django.db.models import Q
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from apps.accounts.models import User

class ConversationListView(generics.ListCreateAPIView):
    serializer_class = ConversationSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user).order_by('-updated_at')

    def create(self, request, *args, **kwargs):
        participant_ids = request.data.get('participants', [])
        if not participant_ids:
            return Response({'error': 'Participants are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Add current user to participants if not present
        if str(request.user.id) not in [str(pid) for pid in participant_ids]:
            participant_ids.append(request.user.id)
        
        # For 1-on-1 chats, check if conversation already exists
        if len(participant_ids) == 2 and not request.data.get('is_group', False):
            existing = Conversation.objects.filter(is_group=False)
            for p_id in participant_ids:
                existing = existing.filter(participants__id=p_id)
            
            if existing.exists():
                serializer = self.get_serializer(existing.first())
                return Response(serializer.data)

        # Create new conversation
        conversation = Conversation.objects.create(
            is_group=request.data.get('is_group', False),
            group_name=request.data.get('group_name', ''),
            created_by=request.user
        )
        # Add participants through the through model
        from .models import ConversationParticipant
        for p_id in participant_ids:
            user = User.objects.get(id=p_id)
            role = 'admin' if user == request.user else 'member'
            ConversationParticipant.objects.create(
                conversation=conversation,
                user=user,
                role=role
            )
        
        serializer = self.get_serializer(conversation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class MessageListView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        conversation_id = self.kwargs['conversation_id']
        return Message.objects.filter(
            conversation_id=conversation_id,
            conversation__participants=self.request.user
        ).order_by('created_at')
