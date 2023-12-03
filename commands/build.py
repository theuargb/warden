#!/usr/bin/python3

import os
from pathlib import Path
from shutil import copyfile


if os.environ['WARDEN_ENV_TYPE'] != 'magento2':
    print('This command is only available for magento2 environments yet.')
    exit(-1)

dockerfile = Path(f"{os.environ['WARDEN_ENV_PATH']}/Dockerfile")
if not dockerfile.exists():
    auth_json_path = Path(f"{os.environ['WARDEN_ENV_PATH']}/auth.json.docker")
    if not auth_json_path.exists():
        print('auth.json.docker is required to fetch magento2 composer dependencies')
        exit(-1)
    with auth_json_path.open() as ajf:
        auth_json = [x[:-1] for x in ajf.readlines()]
        auth_json = '\\\n'.join(auth_json) + '\\'
    config_php_path = Path(f"{os.environ['WARDEN_ENV_PATH']}/app/etc/config.php.docker")
    if not config_php_path.exists():
        print('config.php.docker is required to build a magento2 environment yet not found')
        if 'y' in input('Do you want to create a default config.php.docker file now? (y/[N]): ').lower():
            if not config_php_path.parent.exists():
                os.makedirs(config_php_path.parent)
            with config_php_path.open('w') as cpf:
                cpf.write('''<?php
return [
    'scopes' => [
        'websites' => [
            'admin' => [
                'website_id' => '0',
                'code' => 'admin',
                'name' => 'Admin',
                'sort_order' => '0',
                'default_group_id' => '0',
                'is_default' => '0',
            ],
            'base' => [
                'website_id' => '1',
                'code' => 'base',
                'name' => 'Main Website',
                'sort_order' => '0',
                'default_group_id' => '1',
                'is_default' => '1',
            ],
        ],
        'groups' => [
            0 => [
                'group_id' => '0',
                'website_id' => '0',
                'name' => 'Default',
                'root_category_id' => '0',
                'default_store_id' => '0',
                'code' => 'default',
            ],
            1 => [
                'group_id' => '1',
                'website_id' => '1',
                'name' => 'Main Website Store',
                'root_category_id' => '2',
                'default_store_id' => '1',
                'code' => 'main_website_store',
            ],
        ],
        'stores' => [
            'admin' => [
                'store_id' => '0',
                'code' => 'admin',
                'website_id' => '0',
                'group_id' => '0',
                'name' => 'Admin',
                'sort_order' => '0',
                'is_active' => '1',
            ],
            'default' => [
                'store_id' => '1',
                'code' => 'default',
                'website_id' => '1',
                'group_id' => '1',
                'name' => 'Website',
                'sort_order' => '0',
                'is_active' => '1',
            ],
        ],
    ],
    'themes' => [
        'adminhtml/Magento/backend' => [
            'parent_id' => null,
            'theme_path' => 'Magento/backend',
            'theme_title' => 'Magento 2 backend',
            'is_featured' => '0',
            'area' => 'adminhtml',
            'type' => '0',
            'code' => 'Magento/backend',
        ],
        'frontend/Magento/luma' => [
            'parent_id' => 'Magento/default',
            'theme_path' => 'Magento/luma',
            'theme_title' => 'Luma',
            'is_featured' => '0',
            'area' => 'frontend',
            'type' => '0',
            'code' => 'Magento/luma',
        ],
    ],
    'system' => [
        'default' => [
            'dev' => [
                'css' => [
                    'minify_files' => '1'
                ],
                'js' => [
                    'minify_files' => '1'
                ]
            ]
        ]
    ]
];''')
    with dockerfile.open('w') as df:
        df.write(
f'''

FROM composer as builder
WORKDIR /app/
COPY ./ ./
RUN mkdir ~/.composer && echo '\
{{\\
    "config": {{\\
        "platform":{{\\
            "php": "{os.environ['PHP_VERSION']}",\\
        }}\\
    }}\\
}}\\
' >> ~/.composer/config.json
RUN echo '\
{auth_json}
' >> auth.json
RUN composer install --no-dev --no-interaction --no-progress --ignore-platform-reqs

FROM wardenenv/php-fpm:{os.environ['PHP_VERSION']}-magento2
ARG MODE=production

WORKDIR /var/www/html/

COPY ./ ./
COPY --from=builder /app/vendor ./vendor
RUN sudo chown -R www-data:www-data ./

RUN if [ "$MODE" = "production" ] ; then echo "Mode: Production" \
    && mv app/etc/config.php app/etc/config.php.bak  \
    || cp app/etc/config.php.docker app/etc/config.php \
    && MAGE_MODE=$MODE bin/magento module:enable --all \
    && MAGE_MODE=$MODE bin/magento setup:di:compile \
    && MAGE_MODE=$MODE bin/magento setup:static-content:deploy -f -j4 \
    && rm -rf app/etc/config.php \
    && mv app/etc/config.php.bak app/etc/config.php \
    || rm -rf app/etc/env.php \
; elif [ "$MODE" = "developer" ] ; then echo "Mode: Developer" \
    && MAGE_MODE=$MODE bin/magento \
; else echo "Unknown mode: ${{MODE}}" \
; fi
''')
else:
    php_version = os.environ['PHP_VERSION']
    with dockerfile.open() as df:
        df_lines = df.readlines()
    for i, line in enumerate(df_lines):
        if 'FROM wardenenv/php-fpm' in line:
            from_version = line.split(':')[1].split('-')[0]
            if from_version != php_version:
                if 'y' in input(f'Your .env file specifies php-{php_version} but your Dockerfile specifies {from_version}.\nDo you want to update your Dockerfile? (y/[N]): ').lower():
                    df_lines[i] = f'FROM wardenenv/php-fpm:{php_version}-magento2\n'
                    with dockerfile.open('w') as df:
                        df.write(''.join(df_lines))
        

dockerignore = Path(f"{os.environ['WARDEN_ENV_PATH']}/.dockerignore")
gitignore = Path(f"{os.environ['WARDEN_ENV_PATH']}/.gitignore")
if not dockerignore.exists() and gitignore.exists():
    copyfile(gitignore.absolute(), gitignore.absolute())
if dockerignore.exists():
    with dockerignore.open('r') as di:
        dockerignore_lines = [x.strip() for x in di.readlines()]
else:
    dockerignore_lines = []
with dockerignore.open('a') as di:
    if 'vendor/' not in dockerignore_lines:
        di.write('vendor/\n')
    if '.env' not in dockerignore_lines:
        di.write('.env\n')
    if 'auth.json' not in dockerignore_lines:
        di.write('auth.json\n')
    if '.dockerignore' not in dockerignore_lines:
        di.write('.dockerignore\n')
    if 'Dockerfile' not in dockerignore_lines:
        di.write('Dockerfile\n')
