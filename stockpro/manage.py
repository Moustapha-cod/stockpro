#!/usr/bin/env python
import os, sys

def main():
    # Ajoute le dossier parent au path pour que le package 'stockpro' soit trouvable
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stockpro.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
