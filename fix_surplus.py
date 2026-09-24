import re

with open('templates/redistribution_surplus.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the entire grid container with a dynamic loop
new_content = re.sub(
    r'<div style="display:grid; grid-template-columns:repeat\(auto-fill, minmax\(280px, 1fr\)\); gap:20px;">.*?</div>\s*</div>\s*{% endblock %}',
    '''<div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(280px, 1fr)); gap:20px;">
        {% for item in surplus_items %}
        <div class="form-card" style="display:flex; flex-direction:column; justify-content:space-between; padding:20px;">
            <div>
                <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                    <span class="badge" style="background:var(--success); color:white;">Surplus</span>
                </div>
                <h3 style="margin:0 0 5px; font-size:1.2rem;">{{ item.food_name }}</h3>
                <p style="margin:0 0 15px; color:var(--text-muted); font-size:0.9rem;">From: {{ item.organization.name|default:"Unknown" }}</p>
                <div style="background:var(--color-surface); padding:10px; border-radius:8px; margin-bottom:15px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                        <span style="color:var(--text-muted);">Quantity:</span>
                        <strong>{{ item.quantity }}</strong>
                    </div>
                </div>
            </div>
            <form method="POST" action="{% url 'redistribution_surplus' %}">
                {% csrf_token %}
                <input type="hidden" name="food_id" value="{{ item.id }}">
                <button type="submit" class="btn primary" style="width:100%;">Claim Now</button>
            </form>
        </div>
        {% empty %}
        <p>No surplus food is currently available.</p>
        {% endfor %}
    </div>
</div>
{% endblock %}''',
    content,
    flags=re.DOTALL
)

with open('templates/redistribution_surplus.html', 'w', encoding='utf-8') as f:
    f.write(new_content)
