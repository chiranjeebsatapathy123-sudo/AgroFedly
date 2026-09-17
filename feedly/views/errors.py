from django.shortcuts import render
from django.http import JsonResponse

def is_api_request(request):
    return request.path.startswith('/api/') or request.headers.get('Accept', '').find('application/json') != -1

def custom_400(request, exception):
    if is_api_request(request):
        return JsonResponse({'success': False, 'error': {'code': 'BAD_REQUEST', 'message': 'Bad Request'}}, status=400)
    return render(request, '400.html', status=400)

def custom_403(request, exception):
    if is_api_request(request):
        return JsonResponse({'success': False, 'error': {'code': 'FORBIDDEN', 'message': 'Permission Denied'}}, status=403)
    return render(request, '403.html', status=403)

def custom_404(request, exception):
    if is_api_request(request):
        return JsonResponse({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Resource Not Found'}}, status=404)
    return render(request, '404.html', status=404)

def custom_500(request):
    if is_api_request(request):
        return JsonResponse({'success': False, 'error': {'code': 'SERVER_ERROR', 'message': 'Internal Server Error'}}, status=500)
    return render(request, '500.html', status=500)
