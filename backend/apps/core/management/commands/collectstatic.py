import os
import subprocess
from pathlib import Path
from django.contrib.staticfiles.management.commands.collectstatic import Command as CollectStaticCommand
from django.conf import settings

class Command(CollectStaticCommand):
    """
    Custom collectstatic command that automatically builds the React frontend
    before collecting static files. This ensures the frontend is built during
    Render deployments where we cannot easily change the build command.
    """
    
    def handle(self, *args, **options):
        frontend_dir = Path(settings.BASE_DIR).parent / 'frontend'
        
        # Only attempt to build if the frontend directory exists and contains package.json
        if frontend_dir.exists() and (frontend_dir / 'package.json').exists():
            self.stdout.write(self.style.SUCCESS('Building React frontend automatically...'))
            try:
                # Install dependencies
                self.stdout.write('Running npm install...')
                # Use shell=True for Windows compatibility just in case, though Render is Linux
                subprocess.run(['npm', 'install'], cwd=str(frontend_dir), check=True, shell=os.name == 'nt')
                
                # Build frontend
                self.stdout.write('Running npm run build...')
                subprocess.run(['npm', 'run', 'build'], cwd=str(frontend_dir), check=True, shell=os.name == 'nt')
                
                self.stdout.write(self.style.SUCCESS('Frontend build completed successfully.'))
            except subprocess.CalledProcessError as e:
                self.stdout.write(self.style.ERROR(f'Failed to build frontend. Error: {e}'))
                # We could sys.exit(1) here, but let's allow collectstatic to proceed 
                # in case it's a transient error or they are using a pre-built dist
            except FileNotFoundError:
                self.stdout.write(self.style.WARNING('npm command not found. Skipping frontend build.'))
        else:
            self.stdout.write(self.style.WARNING(f'Frontend directory not found at {frontend_dir}. Skipping build.'))
            
        # Proceed with normal collectstatic
        super().handle(*args, **options)
