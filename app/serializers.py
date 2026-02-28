from rest_framework import serializers

class RouteRequestSerializer(serializers.Serializer):
    start = serializers.CharField()
    end = serializers.CharField()