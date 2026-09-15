import os
import django
from django.conf import settings
from django.template.loader import get_template
from django.template import TemplateSyntaxError

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AgroFedly.settings')
django.setup()

templates_dir = os.path.join(settings.BASE_DIR, 'templates')

def check_templates():
    errors = []
    success_count = 0

    for root, dirs, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                # Get the relative path for the template loader
                rel_path = os.path.relpath(os.path.join(root, file), templates_dir)
                try:
                    # get_template will compile the template and parse tags
                    get_template(rel_path)
                    success_count += 1
                except TemplateSyntaxError as e:
                    errors.append(f"Syntax Error in {rel_path}: {e}")
                except Exception as e:
                    errors.append(f"Other Error in {rel_path}: {e}")
    
    print(f"Checked {success_count + len(errors)} templates.")
    if errors:
        print("\n--- TEMPLATE ERRORS FOUND ---")
        for err in errors:
            print(err)
        return False
    else:
        print("\nAll templates compiled successfully!")
        return True

if __name__ == '__main__':
    success = check_templates()
    if not success:
        exit(1)
