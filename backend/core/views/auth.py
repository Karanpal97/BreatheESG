from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from core.serializers import UserSerializer


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')

        # Support login by email (username field = email in our setup)
        user = authenticate(request, username=email, password=password)
        if not user:
            # Try looking up by email then authenticating
            from core.models import User as AppUser
            try:
                u = AppUser.objects.get(email=email)
                user = authenticate(request, username=u.username, password=password)
            except AppUser.DoesNotExist:
                pass

        if not user:
            return Response({'error': 'Invalid email or password'}, status=400)

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data,
        })


class LogoutView(APIView):
    def post(self, request):
        try:
            request.user.auth_token.delete()
        except Exception:
            pass
        return Response({'status': 'logged out'})


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)
