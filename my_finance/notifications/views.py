from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Notification, NotificationPreference
from .serializers import (
    NotificationSerializer,
    NotificationPreferenceSerializer
)


class NotificationListView(APIView):

    permission_classes = [
        IsAuthenticated
    ]


    def get(self, request):

        notifications = Notification.objects.filter(
            user=request.user,
            enabled=True
        )


        data = []


        for notification in notifications:

            notification_type = notification.type


            data.append({

                "id": notification.id,

                "title":
                    f"notifications.{notification_type}_alert",

                "message":
                    f"notifications.{notification_type}_message",

                "type":
                    notification_type,

                "is_read":
                    notification.is_read,

                "enabled":
                    notification.enabled,

                "created_at":
                    notification.created_at

            })


        return Response(data)



    def post(self, request):

        Notification.objects.filter(
            user=request.user
        ).update(
            is_read=True
        )


        return Response({
            "success": True
        })





class NotificationPreferenceView(APIView):

    permission_classes = [
        IsAuthenticated
    ]


    def get(self, request):

        preference, _ = NotificationPreference.objects.get_or_create(
            user=request.user
        )


        serializer = NotificationPreferenceSerializer(
            preference
        )


        return Response(
            serializer.data
        )



    def put(self, request):

        preference, _ = NotificationPreference.objects.get_or_create(
            user=request.user
        )


        serializer = NotificationPreferenceSerializer(
            preference,
            data=request.data
        )


        if serializer.is_valid():

            serializer.save()

            return Response(
                serializer.data
            )


        return Response(
            serializer.errors,
            status=400
        )