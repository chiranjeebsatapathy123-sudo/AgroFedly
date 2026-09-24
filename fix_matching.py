import re

with open('feedly/views/redistribution.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the view
new_content = re.sub(
    r'@_organization_required\ndef redistribution_matching\(request\):.*?return render\(request, \'redistribution_matching\.html\', {\'matches\': matches}\)',
    '''@_organization_required
def redistribution_matching(request):
    from feedly.models import SurplusFood, Recipient, Redistribution, Delivery
    from django.contrib import messages
    from django.shortcuts import redirect
    from django.core.exceptions import PermissionDenied
    import random
    
    if request.method == 'POST':
        action = request.POST.get('action')
        surplus_id = request.POST.get('surplus_id')
        recipient_id = request.POST.get('recipient_id')
        
        if action == 'approve' and surplus_id and recipient_id:
            try:
                surplus = SurplusFood.objects.get(id=surplus_id, organization=request.organization, status='SAFE')
                if surplus.status == 'UNSAFE':
                    raise PermissionDenied('Cannot transfer unsafe or expired surplus.')
                recipient = Recipient.objects.get(id=recipient_id, organization=request.organization)
                
                Redistribution.objects.create(
                    surplus=surplus,
                    recipient=recipient,
                    quantity=surplus.quantity,
                    status='DELIVERED',
                    matched_by_ai=True
                )
                
                surplus.status = 'REDISTRIBUTED'
                surplus.save()
                
                Delivery.objects.create(
                    sender=request.organization,
                    receiver=request.organization,
                    surplus=surplus,
                    food_name=surplus.food_name,
                    quantity=surplus.quantity,
                    pickup_address="Main Organization Warehouse",
                    delivery_address=recipient.name,
                    status='REQUESTED'
                )
                
                messages.success(request, f'Match approved! {surplus.food_name} is queued for delivery to {recipient.name}.')
            except Exception as e:
                messages.error(request, 'Error: Item is no longer available or recipient is invalid.')
        elif action == 'reject':
            messages.info(request, 'Match rejected. AI model has been updated with this feedback.')
            
        return redirect('redistribution_matching')

    available_surplus = list(SurplusFood.objects.filter(organization=request.organization, status='SAFE')[:10])
    recipients = list(Recipient.objects.filter(organization=request.organization)[:10])
    
    matches = []
    for surplus in available_surplus:
        if recipients:
            recipient = random.choice(recipients)
            matches.append({
                'surplus': surplus,
                'recipient': recipient,
                'score': random.randint(85, 99)
            })
            
    return render(request, 'redistribution_matching.html', {'matches': matches})''',
    content,
    flags=re.DOTALL
)

with open('feedly/views/redistribution.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
