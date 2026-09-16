from rest_framework import serializers
from .models import Ticket, TicketCategory, SLA, TicketComment, TicketRating
from users.serializers import UserSerializer, CompanySerializer

class SLASerializer(serializers.ModelSerializer):
    class Meta:
        model = SLA
        fields = '__all__'

class TicketCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketCategory
        fields = '__all__'

class TicketCommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = TicketComment
        fields = ['id', 'ticket', 'author', 'content', 'created_at']
        read_only_fields = ['ticket', 'author', 'created_at']

class TicketRatingSerializer(serializers.ModelSerializer):
    client = UserSerializer(read_only=True)

    class Meta:
        model = TicketRating
        fields = ['id', 'ticket', 'client', 'rating', 'feedback', 'created_at']
        read_only_fields = ['ticket', 'client', 'created_at']

class TicketSerializer(serializers.ModelSerializer):
    category_detail = TicketCategorySerializer(source='category', read_only=True)
    creator_detail = UserSerializer(source='creator', read_only=True)
    assignee_detail = UserSerializer(source='assignee', read_only=True)
    company_detail = CompanySerializer(source='company', read_only=True)

    comments = TicketCommentSerializer(many=True, read_only=True)
    rating = TicketRatingSerializer(read_only=True)

    class Meta:
        model = Ticket
        fields = [
            'id', 'title', 'description', 'status', 'priority',
            'category', 'category_detail', 'company', 'company_detail',
            'creator', 'creator_detail', 'assignee', 'assignee_detail',
            'created_at', 'updated_at', 'response_deadline', 'resolution_deadline',
            'first_response_at', 'resolved_at', 'comments', 'rating'
        ]
        read_only_fields = [
            'creator', 'company', 'created_at', 'updated_at',
            'response_deadline', 'resolution_deadline', 'first_response_at', 'resolved_at'
        ]
