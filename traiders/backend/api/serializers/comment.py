from rest_framework import serializers, fields
from rest_framework.exceptions import PermissionDenied

from ..models import ArticleComment, EquipmentComment, Equipment
from . import UserSerializer


class IsLiked(serializers.BooleanField):
    def get_attribute(self, instance):
        if self.context['request'].user.is_anonymous:
            return False
        return instance.liked_by.filter(pk=self.context['request'].user.pk).exists()


class CommentSerializerBase(serializers.HyperlinkedModelSerializer):
    user = UserSerializer(read_only=True)
    is_liked = IsLiked(required=False)
    num_likes = serializers.SerializerMethodField(read_only=True)

    def get_num_likes(self, comment):
        return comment.liked_by.count()

    def validate(self, data):
        # If only liking, user does not have to provide any content or image
        if self.context['request'].method != 'PATCH':
            if not data.get('image') and not data.get('content'):
                raise serializers.ValidationError("Please either provide an image or a text as the comment.")
        return data

    def create(self, validated_data: dict):
        if 'is_liked' in validated_data:
            validated_data.pop('is_liked')

        validated_data['user'] = self.context['request'].user

        return super().create(validated_data)

    def update(self, instance, validated_data: dict):
        is_liked = validated_data.pop('is_liked', None)
        likers = instance.liked_by.all()

        if validated_data and self.context['request'].user != instance.user:
            raise PermissionDenied

        if is_liked is True:
            if self.context['request'].user.is_anonymous:
                raise serializers.ValidationError('A guest user cannot like a comment. '
                                                  'Please login to perform this action.')
            if self.context['request'].user in likers:
                raise serializers.ValidationError('You already like this comment.')
            instance.liked_by.add(self.context['request'].user)
        elif is_liked is False:
            if self.context['request'].user.is_anonymous:
                raise serializers.ValidationError('A guest user cannot unlike a comment '
                                                  'Please login to perform this action.')
            if self.context['request'].user not in likers:
                raise serializers.ValidationError('You already do not like this comment.')
            instance.liked_by.remove(self.context['request'].user)

        return super().update(instance, validated_data)


class ArticleCommentSerializer(CommentSerializerBase):
    def get_fields(self):
        fields = super().get_fields()

        view = self.context.get('view')
        if view and getattr(view, 'action') != 'create':
            fields['article'].read_only = True

        return fields

    class Meta:
        model = ArticleComment
        fields = ["id", "url", "created_at", "content", "image", "user",
                  "article", "is_liked", "liked_by", "num_likes"]
        read_only_fields = ['id', 'url', 'created_at', 'user',
                            'liked_by', 'is_liked', 'num_likes']


class EquipmentCommentSerializer(CommentSerializerBase):

    class EquipmentField(serializers.CharField):
        def get_attribute(self, instance):
            return instance.equipment.symbol

        def run_validation(self, symbol=fields.empty):
            super().run_validation(symbol)
            equipment = Equipment.objects.filter(symbol=symbol).first()
            if equipment is None:
                raise serializers.ValidationError('No such equipment')
            return equipment

    equipment = EquipmentField()

    def get_fields(self):
        fields = super().get_fields()

        view = self.context.get('view')
        if view and getattr(view, 'action') != 'create':
            fields['equipment'].read_only = True

        return fields

    class Meta:
        model = EquipmentComment
        fields = ["id", "url", "created_at", "content",
                  "image", "user", "equipment", "is_liked", "liked_by", "num_likes"]
        read_only_fields = ['id', 'url', 'created_at', 'user',
                            'liked_by', 'is_liked', 'num_likes']
