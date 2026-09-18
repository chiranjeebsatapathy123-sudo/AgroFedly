from django.shortcuts import render

def index(request):
    """Public Landing Page."""
    return render(request, 'public/index.html')

def product(request):
    """Product details page."""
    return render(request, 'public/product.html')

def solutions(request):
    """Solutions for various personas."""
    return render(request, 'public/solutions.html')

def ai(request):
    """Details about the AgroFedly AI ecosystem."""
    return render(request, 'public/ai.html')

def features(request):
    """Feature grid and explanation."""
    return render(request, 'public/features.html')

def pricing(request):
    """Pricing and plans."""
    return render(request, 'public/pricing.html')

def about(request):
    """About the company."""
    return render(request, 'public/about.html')

def security(request):
    """Security practices."""
    return render(request, 'public/security.html')

def privacy(request):
    """Privacy policy."""
    return render(request, 'public/privacy.html')

def terms(request):
    """Terms of Service."""
    return render(request, 'public/terms.html')

from django.contrib import messages
from django.shortcuts import redirect

def contact(request):
    """Contact page."""
    if request.method == 'POST':
        # Simulated email/database action
        name = request.POST.get('name')
        messages.success(request, f"Thank you {name}, your message has been sent successfully!")
        return redirect('contact')
    return render(request, 'public/contact.html')

from django.http import JsonResponse

def api_weather(request):
    return JsonResponse({'status': 'ok'})
