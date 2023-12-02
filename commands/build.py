#!/usr/bin/python3

import os
from pathlib import Path
from shutil import copyfile


dockerfile = Path(f"{os.environ('WARDEN_ENV_PATH')}/Dockerfile")
if not dockerfile.exists():
    if os.environ('WARDEN_ENV_TYPE') == 'magento2':
        auth_json_path = Path(f"{os.environ('WARDEN_ENV_PATH')}/auth.json.docker")
        if not auth_json_path.exists():
            print('auth.json.docker is required to fetch magento2 composer dependencies')
        with auth_json_path.open() as ajf:
            auth_json = ajf.readlines()
            auth_json = '\\\n'.join(auth_json)
        with dockerfile.open('w') as df:
            df.write(f'''
FROM composer as builder
WORKDIR /app/
COPY ./ ./
RUN echo '\
{auth_json}
' >> auth.json
RUN composer install --no-dev --no-interaction --no-progress --optimize-autoloader

FROM wardenenv/php-fpm:8.1-magento2

WORKDIR /var/www/html/

COPY ./ ./
RUN sudo chown -R www-root:www-root ./

COPY --from=builder /app/vendor ./vendor

RUN mv app/etc/config.php app/etc/config.php.bak  \
    || cp app/etc/config.php.docker app/etc/config.php \
    && bin/magento module:enable --all \
    && bin/magento setup:di:compile \
    && bin/magento setup:static-content:deploy -f \
    && rm -rf app/etc/config.php \
    && mv app/etc/config.php.bak app/etc/config.php \
    || echo
''')
        

dockerignore = Path(f"{os.environ('WARDEN_ENV_PATH')}/.dockerignore")
gitignore = Path(f"{os.environ('WARDEN_ENV_PATH')}/.gitignore")
if not dockerignore.exists() and gitignore.exists():
    copyfile(gitignore.absolute(), gitignore.absolute())

