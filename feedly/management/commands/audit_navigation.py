import sys
from django.core.management.base import BaseCommand
from django.urls import reverse, resolve
from django.urls.exceptions import NoReverseMatch
from feedly.services.workspaces import WORKSPACE_CONFIGS

class Command(BaseCommand):
    help = 'Audits all workspace navigation links to ensure they are fully implemented'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Starting Phase 49 Workspace Navigation Audit..."))
        
        # Format strings for table output
        header = f"{'WORKSPACE':<15} | {'NAV ITEM':<20} | {'URL_NAME':<30} | {'RESOLVED':<20} | {'STATUS'}"
        self.stdout.write("-" * len(header))
        self.stdout.write(header)
        self.stdout.write("-" * len(header))
        
        missing_count = 0
        passed_count = 0
        total_count = 0
        
        for workspace_key, config in WORKSPACE_CONFIGS.items():
            for item in config.get('sidebar', []):
                total_count += 1
                workspace = workspace_key
                nav_item = item.get('label')
                url_name = item.get('url_name')
                resolved_url = "NO URL"
                status = self.style.ERROR("MISSING")
                
                try:
                    resolved_url = reverse(url_name)
                    # Test if view resolves
                    try:
                        view_func, _, _ = resolve(resolved_url)
                        status = self.style.SUCCESS("PASS")
                        passed_count += 1
                    except Exception as e:
                        status = self.style.ERROR("NO VIEW")
                        missing_count += 1
                except NoReverseMatch:
                    status = self.style.ERROR("NO REVERSE MATCH")
                    missing_count += 1
                except Exception as e:
                    status = self.style.ERROR(f"ERROR: {str(e)}")
                    missing_count += 1
                    
                row = f"{workspace:<15} | {str(nav_item):<20} | {str(url_name):<30} | {str(resolved_url):<20} | {status}"
                self.stdout.write(row)
                
        self.stdout.write("-" * len(header))
        self.stdout.write(self.style.MIGRATE_HEADING(f"Audit Complete: {passed_count}/{total_count} Passed, {missing_count} Missing."))
        
        if missing_count > 0:
            sys.exit(1)
