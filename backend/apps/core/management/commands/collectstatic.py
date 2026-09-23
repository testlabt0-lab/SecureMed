import shutil
import subprocess
from pathlib import Path
from django.contrib.staticfiles.management.commands.collectstatic import Command as CollectStaticCommand
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(CollectStaticCommand, BaseCommand):
    """
    Custom collectstatic command that automatically builds the React frontend
    before collecting static files. This ensures the frontend is built during
    Render deployments where we cannot easily change the build command.

    ``BaseCommand`` is listed explicitly even though ``CollectStaticCommand``
    already subclasses it: the front-end build behaviour lives in the parent's
    ``handle``, but the Django management-command contract this class must
    satisfy is ``BaseCommand`` itself, and stating it keeps that contract
    visible without the reader having to follow an aliased import.
    """
    
    def handle(self, *args, **options):
        frontend_dir = Path(settings.BASE_DIR).parent / 'frontend'
        
        # Only attempt to build if the frontend directory exists and contains package.json
        if frontend_dir.exists() and (frontend_dir / 'package.json').exists():
            # Resolve npm to an absolute path (npm.cmd on Windows, npm elsewhere)
            # so the subprocess calls below never need shell=True. A resolved
            # executable is portable across platforms and avoids the shell-
            # injection surface (bandit B602) that ``shell=os.name == 'nt'``
            # carried — that flag also made the command line non-constant, so
            # a scanner could not tell it was safe.
            npm = shutil.which('npm')
            if npm is None:
                self.stdout.write(self.style.WARNING('npm command not found. Skipping frontend build.'))
            else:
                self.stdout.write(self.style.SUCCESS('Building React frontend automatically...'))
                try:
                    self.stdout.write('Running npm install...')
                    subprocess.run([npm, 'install'], cwd=str(frontend_dir), check=True)
                    
                    self.stdout.write('Running npm run build...')
                    subprocess.run([npm, 'run', 'build'], cwd=str(frontend_dir), check=True)
                    
                    self.stdout.write(self.style.SUCCESS('Frontend build completed successfully.'))
                except subprocess.CalledProcessError as e:
                    self.stdout.write(self.style.ERROR(f'Failed to build frontend. Error: {e}'))
                    # We could sys.exit(1) here, but let's allow collectstatic to proceed 
                    # in case it's a transient error or they are using a pre-built dist
                except FileNotFoundError:
                    self.stdout.write(self.style.WARNING('npm resolved but could not be run. Skipping frontend build.'))
        else:
            self.stdout.write(self.style.WARNING(f'Frontend directory not found at {frontend_dir}. Skipping build.'))
            
        # Proceed with normal collectstatic
        super().handle(*args, **options)
