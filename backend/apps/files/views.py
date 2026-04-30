from rest_framework import generics, permissions
from .models import Attachment
from .serializers import AttachmentSerializer

class AttachmentCreateView(generics.CreateAPIView):
    serializer_class = AttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)
