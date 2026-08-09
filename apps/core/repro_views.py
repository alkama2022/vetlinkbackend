import time

from django.http import JsonResponse


def slow_view(request):
    time.sleep(15)
    return JsonResponse({'ok': True})
