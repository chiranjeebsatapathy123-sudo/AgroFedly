import re

with open('templates/admin_organizations.html', 'r', encoding='utf-8') as f:
    content = f.read()

new_content = re.sub(
    r'<tr style="border-bottom: 1px solid #eee;">\s*<td style="padding:15px 10px; font-weight:bold;">Sunnydale Farms</td>.*?</tr>\s*<tr style="border-bottom: 1px solid #eee;">\s*<td style="padding:15px 10px; font-weight:bold;">Downtown Soup Kitchen</td>.*?</tr>\s*<tr style="border-bottom: 1px solid #eee;">\s*<td style="padding:15px 10px; font-weight:bold;">Local Dairy Co-op</td>.*?</tr>',
    '''                {% for org in organizations %}
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding:15px 10px; font-weight:bold;">{{ org.name }}</td>
                    <td style="padding:15px 10px;">{{ org.get_organization_type_display }}</td>
                    <td style="padding:15px 10px;">{{ org.created_at|date:"M d, Y" }}</td>
                    <td style="padding:15px 10px;">
                        {% if org.is_active %}
                            <span class="badge" style="background:var(--success); color:white;">Active</span>
                        {% else %}
                            <span class="badge" style="background:var(--warning); color:white;">Inactive</span>
                        {% endif %}
                    </td>
                    <td style="padding:15px 10px;">
                        <button class="btn" style="padding:5px 10px; font-size:0.8rem;" onclick="alert('This feature is coming soon!'); return false;">Edit</button>
                    </td>
                </tr>
                {% empty %}
                <tr>
                    <td colspan="5" style="padding:15px 10px; text-align:center;">No organizations found.</td>
                </tr>
                {% endfor %}''',
    content,
    flags=re.DOTALL
)

with open('templates/admin_organizations.html', 'w', encoding='utf-8') as f:
    f.write(new_content)
