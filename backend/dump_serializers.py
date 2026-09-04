import os 
import django 
import sys 

# Comment_1
sys .path .append (os .path .dirname (os .path .abspath (__file__ )))
os .environ .setdefault ('DJANGO_SETTINGS_MODULE','config.dev_settings')
django .setup ()

def dump_app (app_name ):
    try :
        import importlib 
        serializers =importlib .import_module (f'apps.{app_name }.serializers')
        print (f"\n--- {app_name .upper ()} ---")
        for name in dir (serializers ):
            if name .endswith ('Serializer')and name !='Serializer'and name !='ModelSerializer':
                cls =getattr (serializers ,name )
                if hasattr (cls ,'Meta')and hasattr (cls .Meta ,'fields'):
                    print (f"{name }: {cls .Meta .fields }")
                elif hasattr (cls ,'_declared_fields'):
                # Comment_2
                    try :
                        print (f"{name }: {list (cls ().get_fields ().keys ())}")
                    except :
                        print (f"{name }: {[k for k in cls ._declared_fields .keys ()]}")
    except Exception as e :
        print (f"Error in {app_name }: {e }")

for app in ['pharmacy','lab','appointments','telemedicine']:
    dump_app (app )
