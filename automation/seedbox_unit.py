"""Render the one bounded user service; never install/start it from this module."""
import re
from pathlib import Path
from ai_movie_investigator.contracts import require,hash_id


def render(python,bootstrap,manifest,manifest_sha256,configuration,configuration_sha256):
    for value in (python,bootstrap,manifest,configuration):
        require(type(value) is str and value.startswith('/') and re.fullmatch(r'[A-Za-z0-9_./-]+',value),'host_unit_path')
    hash_id(manifest_sha256);hash_id(configuration_sha256)
    return '\n'.join(('[Unit]','Description=Movie assessment event worker','StartLimitIntervalSec=600','StartLimitBurst=3','',
        '[Service]','Type=simple','UMask=0077','NoNewPrivileges=yes','LimitCORE=0','RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6',
        'ExecStart=/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C.UTF-8 '+python+' -I -B '+bootstrap+' '+manifest+' '+manifest_sha256+' run '+configuration+' '+configuration_sha256,
        'Restart=on-failure','RestartSec=30','TimeoutStopSec=20','KillMode=control-group','',
        '[Install]','WantedBy=default.target',''))
