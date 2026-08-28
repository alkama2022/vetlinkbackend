from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.chat.models import (
    Conversation,
    ConversationParticipant,
    Message,
    MessageAttachment,
    MessageReadReceipt,
    is_blocked,
)
from apps.chat.serializers import (
    ChatUserBriefSerializer,
    ConversationCreateSerializer,
    ConversationSerializer,
    MessageCreateSerializer,
    MessageSerializer,
    get_or_create_direct_conversation,
)
from apps.chat.ws import broadcast_to_users

MESSAGE_PAGE_SIZE = 40


def _serialize_message(message, request):
    return MessageSerializer(message, context={'request': request}).data


def _participant_ids(conversation):
    return list(conversation.participants.values_list('user_id', flat=True))


def _broadcast(kind, payload, user_ids):
    # Channels dispatcher expects underscored type names; normalize dots to underscores
    channel_type = kind.replace('.', '_')
    broadcast_to_users(user_ids, {'type': channel_type, 'payload': payload})


def _kind_for_upload(uploaded, kinds, index):
    mime = getattr(uploaded, 'content_type', '')
    if index < len(kinds):
        label = str(kinds[index])
        if label in ('image', 'video', 'voice', 'audio', 'document', 'animal',
                     'lab_record', 'disease_report', 'prescription'):
            # normalize voice/audio
            if label in ('voice', 'audio'):
                return 'voice'
            return label
    if mime.startswith('image/'):
        return 'image'
    if mime.startswith('video/'):
        return 'video'
    if mime.startswith('audio/'):
        return 'voice'
    return 'document'


def _validate_upload(uploaded):
    allowed = getattr(settings, 'CHAT_ALLOWED_UPLOADS', (
        'image/jpeg', 'image/png', 'image/webp', 'image/gif',
        'video/mp4', 'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ))
    mime = getattr(uploaded, 'content_type', 'application/octet-stream') or ''
    # Normalize audio mime parameters like "audio/webm;codecs=opus"
    base_mime = mime.split(';')[0].strip().lower()
    if base_mime in [a.lower() for a in allowed]:
        return True
    # Fallback: accept any image/video/audio prefix if not explicitly listed but reasonable
    if base_mime.startswith('image/') or base_mime.startswith('video/') or base_mime.startswith('audio/'):
        return True
    return mime in allowed


class ConversationViewSet(viewsets.ModelViewSet):
    """Conversations the current user participates in."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ConversationSerializer
    queryset = Conversation.objects.none()

    def get_queryset(self):
        return (
            Conversation.objects.filter(participants__user=self.request.user)
            .prefetch_related('participants__user', 'participants__user__chat_presence')
            .distinct()
            .order_by('-last_message_at')
        )

    def create(self, request, *args, **kwargs):
        serializer = ConversationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        other = serializer.validated_data.get('user_obj') or serializer.validated_data.get('user_id')

        if is_blocked(request.user, other):
            return Response(
                {'detail': 'You cannot open a conversation with this user.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        conversation = get_or_create_direct_conversation(request.user, other)
        return Response(
            ConversationSerializer(conversation, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Cursor-paginated message history (oldest → newest within a page)."""
        conversation = self.get_object()
        try:
            limit = int(request.query_params.get('limit', MESSAGE_PAGE_SIZE))
        except (TypeError, ValueError):
            limit = MESSAGE_PAGE_SIZE
        limit = max(1, min(limit, 50))

        qs = (
            conversation.messages.filter(is_deleted=False)
            .select_related('sender')
            .prefetch_related('attachments', 'read_receipts')
        )
        before = request.query_params.get('before')
        if before:
            try:
                qs = qs.filter(id__lt=int(before))
            except (ValueError, TypeError):
                pass

        page = list(qs.order_by('-id')[:limit][::-1])
        has_more = False
        if page:
            has_more = qs.filter(id__lt=page[0].id).exists()

        return Response({
            'results': [_serialize(m, request) for m in page],
            'before': page[0].id if page else None,
            'has_more': bool(has_more),
        })

    @action(detail=True, methods=['get'], url_path='messages/search')
    def search_messages(self, request, pk=None):
        conversation = self.get_object()
        q = (request.query_params.get('q') or '').strip()
        if not q:
            return Response({'results': []})
        qs = (
            conversation.messages.filter(is_deleted=False, content__icontains=q)
            .select_related('sender')
            .prefetch_related('attachments', 'read_receipts')
            .order_by('-id')[:30]
        )
        return Response({
            'results': [_serialize_message(m, request) for m in qs],
        })

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        conversation = self.get_object()
        _mark_conversation_read(request.user, conversation)
        peers = [uid for uid in _participant_ids(conversation) if uid != request.user.id]
        _broadcast('conversation.read', {
            'conversation_id': str(conversation.id),
            'reader_id': str(request.user.id),
        }, peers + [request.user.id])
        return Response({'status': 'read'})


def _mark_conversation_read(user, conversation):
    participant = ConversationParticipant.objects.filter(
        conversation=conversation, user=user
    ).first()
    if not participant:
        return
    now = timezone.now()
    pending = (
        conversation.messages.filter(is_deleted=False)
        .exclude(sender=user)
        .filter(created_at__lte=now)
    )
    receipts = [MessageReadReceipt(message=m, user=user) for m in pending]
    MessageReadReceipt.objects.bulk_create(receipts, ignore_conflicts=True)
    participant.last_read_at = now
    participant.save(update_fields=['last_read_at'])


class MessageViewSet(viewsets.ModelViewSet):
    """Create / read / delete messages inside conversations you belong to."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MessageSerializer
    queryset = Message.objects.none()

    def get_queryset(self):
        qs = Message.objects.filter(conversation__participants__user=self.request.user).distinct()
        conversation_id = self.request.query_params.get('conversation') or self.request.query_params.get('conversation_id')
        if conversation_id:
            try:
                qs = qs.filter(conversation_id=conversation_id)
            except Exception:
                pass
        # Search within conversation if q provided
        q = self.request.query_params.get('q')
        if q:
            qs = qs.filter(content__icontains=q.strip())
        return qs

    def list(self, request, *args, **kwargs):
        """Paginated list: ?conversation=<id>&page=&page_size= or cursor ?before="""
        qs = self.get_queryset().select_related('sender').prefetch_related('attachments', 'read_receipts')
        # Cursor-based if before param present, else standard ordering
        before = request.query_params.get('before')
        if before:
            try:
                qs = qs.filter(id__lt=int(before))
            except (ValueError, TypeError):
                pass
            limit = int(request.query_params.get('limit', MESSAGE_PAGE_SIZE))
            limit = max(1, min(limit, 100))
            page = list(qs.order_by('-id')[:limit][::-1])
            has_more = False
            if page:
                has_more = qs.filter(id__lt=page[0].id).exists()
            return Response({
                'results': [MessageSerializer(m, context={'request': request}).data for m in page],
                'count': len(page),
                'has_more': bool(has_more),
                'before': page[0].id if page else None,
            })
        # Default: order by id ascending and paginate via page params
        qs = qs.order_by('id')
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation_id = serializer.validated_data.get('conversation_id')
        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except (Conversation.DoesNotExist, ValueError, TypeError):
            return Response(
                {'detail': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND
            )

        is_participant = ConversationParticipant.objects.filter(
            conversation=conversation, user=request.user
        ).exists()
        if not is_participant:
            return Response(
                {'detail': 'You are not a participant of this conversation.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        other = ConversationParticipant.objects.filter(conversation=conversation).exclude(
            user=request.user
        ).first()
        if other and is_blocked(request.user, other.user):
            return Response(
                {'detail': 'Messaging is currently blocked in this conversation.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        client_id = serializer.validated_data.get('client_message_id') or ''
        if client_id:
            existing = Message.objects.filter(
                conversation=conversation, sender=request.user, client_message_id=client_id
            ).first()
            if existing:
                return Response(
                    _serialize_message(existing, request), status=status.HTTP_201_CREATED
                )

        content = (serializer.validated_data.get('content') or '').strip()
        files = list(request.FILES.getlist('attachments')) or list(request.FILES.getlist('files'))
        if not content and not files:
            return Response(
                {'detail': 'A message requires text or an attachment.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for uploaded in files:
            if uploaded.size > getattr(settings, 'MAX_UPLOAD_SIZE', 8 * 1024 * 1024):
                return Response(
                    {'detail': f'File "{uploaded.name}" exceeds the size limit.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not _validate_upload(uploaded):
                return Response(
                    {'detail': f'File "{uploaded.name}" is not an allowed type.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        message_type = serializer.validated_data.get('message_type') or 'message'
        kinds = serializer.validated_data.get('file_kinds') or []

        with transaction.atomic():
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                message_type=message_type,
                content=content,
                context=serializer.validated_data.get('context') or '',
                context_id=serializer.validated_data.get('context_id') or '',
                context_title=serializer.validated_data.get('context_title') or '',
                client_message_id=client_id,
                reply_to_id=serializer.validated_data.get('reply_to'),
            )

            if files:
                for index, uploaded in enumerate(files):
                    kind = _kind_for_upload(uploaded, kinds, index)
                    MessageAttachment.objects.create(
                        message=message,
                        file=uploaded,
                        filename=uploaded.name or 'attachment',
                        mime_type=getattr(uploaded, 'content_type', 'application/octet-stream'),
                        size=uploaded.size,
                        kind=kind,
                    )
                if message_type in ('', 'message'):
                    first_kind = _kind_for_upload(files[0], kinds, 0)
                    if first_kind != 'document':
                        message.message_type = first_kind
                        message.save(update_fields=['message_type'])

            conversation.last_message_at = timezone.now()
            conversation.save(update_fields=['last_message_at'])

        _broadcast('message.new', _serialize_message(message, request),
                   _participant_ids(conversation) + [request.user.id])
        return Response(_serialize_message(message, request), status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        message = self.get_object()
        if message.sender_id != request.user.id:
            return Response(
                {'detail': 'You can only delete your own messages.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        message.delete()
        _broadcast('message.deleted', {
            'conversation_id': str(message.conversation_id),
            'id': message.id,
        }, _participant_ids(message.conversation) + [request.user.id])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatContactsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChatUserBriefSerializer

    def get(self, request):
        q = (request.query_params.get('q') or '').strip()
        role = (request.query_params.get('user_type') or '').strip()
        queryset = User.objects.filter(is_active=True).exclude(id=request.user.id)
        if q:
            queryset = queryset.filter(
                models.Q(full_name__icontains=q) | models.Q(email__icontains=q) | models.Q(lga__icontains=q)
            )
        if role:
            queryset = queryset.filter(user_type=role)
        users = queryset.select_related('chat_presence').order_by('full_name')[:20]
        return Response(
            ChatUserBriefSerializer(users, many=True, context={'request': request}).data
        )