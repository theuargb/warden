#!/usr/bin/python3

import sys
import os
from pathlib import Path
import yaml


image = sys.argv[1]
unpack = '-u' in sys.argv or '--unpack' in sys.argv
post = None
for i in range(len(sys.argv)):
    if '-p' in sys.argv[i] or '--post' in sys.argv[i]:
        if '-p=' in sys.argv[i] or '--post=' in sys.argv[i]:
            post = sys.argv[i].split('=')[1]
        else:
            post = sys.argv[i + 1]
        break


if os.environ['WARDEN_ENV_TYPE'] != 'magento2':
    print('This command is only available for magento2 environments yet.')
    exit(-1)

env_root = Path(os.environ['WARDEN_ENV_PATH'])
warden_env = Path(f'{env_root}/.warden/warden-env.yml')
if warden_env.exists():
    with warden_env.open() as wef:
        we = yaml.safe_load(wef)
else:
    if not Path(f'{env_root}/.warden').exists():
        os.makedirs(f'{env_root}/.warden')
    we = {
        'version': '3',
    }


if 'services' not in we or we['services'] is None:
    we['services'] = {}

if 'php-fpm' not in we['services'] or we['services']['php-fpm'] is None:
    we['services']['php-fpm'] = {}

we['services']['php-fpm']['image'] = image

if 'volumes' not in we['services']['php-fpm'] or we['services']['php-fpm']['volumes'] is None:
    we['services']['php-fpm']['volumes'] = []
else:
    i = 0
    while i < len(we['services']['php-fpm']['volumes']):
        if ':/var/www/html/' in we['services']['php-fpm']['volumes'][i]:
            we['services']['php-fpm']['volumes'].pop(i)
        else:
            i += 1
we['services']['php-fpm']['volumes'].append((f'{env_root.absolute()}' if unpack else 'wwwroot') + ':/var/www/html/')
if not unpack:
    we['services']['php-fpm']['volumes'].append(f'{env_root.absolute()}/app/etc/env.php:/var/www/html/app/etc/env.php')

if 'nginx' not in we['services'] or we['services']['nginx'] is None:
    we['services']['nginx'] = {}

if 'volumes' not in we['services']['nginx'] or we['services']['nginx']['volumes'] is None:
    we['services']['nginx']['volumes'] = []
else:
    i = 0
    while i < len(we['services']['nginx']['volumes']):
        if ':/var/www/html/' in we['services']['nginx']['volumes'][i]:
            we['services']['nginx']['volumes'].pop(i)
        else:
            i += 1
we['services']['nginx']['volumes'].append((f'{env_root.absolute()}' if unpack else 'wwwroot') + ':/var/www/html/')


if 'volumes' not in we or we['volumes'] is None:
    we['volumes'] = {}
if not unpack:
    we['volumes']['wwwroot'] = None

with warden_env.open('w+') as wef:
    yaml.dump(we, wef)

if unpack:
    deploy_ignore = Path(f'{env_root}/.warden/.deployignore')
    di = []
    if deploy_ignore.exists():
        with deploy_ignore.open() as dif:
            di = dif.readlines()
    di += ['.warden/', '.env']
    
    def purge(directory = os.environ['WARDEN_ENV_PATH']):
        directory = Path(directory)
        if f'{directory.relative_to(os.environ['WARDEN_ENV_PATH'])}/' in di:
            return
        
        for item in directory.iterdir():
            if item.is_dir():
                purge(item)
            else:
                if f'{item.relative_to(os.environ['WARDEN_ENV_PATH'])}' in di:
                    continue
                item.unlink()
        
        if directory != os.environ['WARDEN_ENV_PATH']:
            try:
                directory.rmdir()
            except OSError as e:
                if e.errno != 39:  # Directory not empty
                    raise
    
    purge()
    
    os.system(
        f'docker rm {os.environ['WARDEN_ENV_NAME']}_deploy_fs' 
        + f' && docker create --name {os.environ['WARDEN_ENV_NAME']}_deploy_fs {image}' 
        + f' && docker cp {os.environ['WARDEN_ENV_NAME']}_deploy_fs:/var/www/html/. {env_root.absolute()}'
        + f' && docker rm {os.environ['WARDEN_ENV_NAME']}_deploy_fs'
    )

os.system(f'docker pull {image}')
os.system('warden env down')
os.system('warden env rm php-fpm -fsv')
os.system(f'docker volume rm {os.environ['WARDEN_ENV_NAME']}_wwwroot -f')
os.system('warden env up')
if post:
    os.system(f'warden env exec php-fpm {post}')
