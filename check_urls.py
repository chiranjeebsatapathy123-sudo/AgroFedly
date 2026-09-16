import os
import re
import django
from django.conf import settings
from django.urls import get_resolver

# Minimal setup to load URLs
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AgroFedly.settings')
django.setup()

def get_all_url_names():
    resolver = get_resolver()
    url_names = set()
    for name, _ in resolver.reverse_dict.items():
        if isinstance(name, str):
            url_names.add(name)
    return url_names

def find_urls_in_templates(templates_dir):
    url_pattern = re.compile(r'{%\s*url\s+[\'"]([a-zA-Z0-9_-]+)[\'"].*?%}')
    all_urls = set()
    template_files = []
    
    for root, _, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    found = url_pattern.findall(content)
                    for url_name in found:
                        all_urls.add(url_name)
    return all_urls

if __name__ == "__main__":
    valid_names = get_all_url_names()
    template_urls = find_urls_in_templates('templates')
    
    missing = template_urls - valid_names
    if missing:
        print("FOUND BROKEN URLS:")
        for m in sorted(missing):
            print(f"- {m}")
    else:
        print("All template URLs are valid!")
