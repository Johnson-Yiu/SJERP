"""Read-only URL inventory; entries are candidates, not permission verdicts."""
import json
import os
import re
import sys
from pathlib import Path

repo = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo / 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.urls import URLPattern, URLResolver, get_resolver
from crm.permissions import PATH_MODULES, action_for_request, module_for_request
from django.contrib.auth.models import AnonymousUser
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory


def walk(patterns, prefix=''):
    for pattern in patterns:
        path = prefix + str(pattern.pattern)
        if isinstance(pattern, URLResolver):
            yield from walk(pattern.url_patterns, path)
        elif isinstance(pattern, URLPattern) and path.startswith('api/'):
            callback = pattern.callback
            cls = getattr(callback, 'cls', getattr(callback, 'view_class', None))
            actions = getattr(callback, 'actions', {})
            permissions = getattr(cls, 'permission_classes', ()) if cls else ()
            declared = getattr(cls, 'permission_module', None) if cls else None
            if declared is not None and not isinstance(declared, str):
                declared = 'DYNAMIC: inspect view'
            root = path.removeprefix('api/').split('/')[0].lstrip('^')
            default = PATH_MODULES.get(root)
            special = {'media': 'file owner and private-media checks', 'context': 'entity-dependent module and object scope',
                       'session': 'identity endpoint; inspect view', 'operation-logs': 'entity/query-dependent module and scope',
                       'actual-rmb-cash': 'view-owned finance permission', 'finance-ledger': 'dynamic view-owned finance permission',
                       'rmb-cash-events': 'view-owned finance permission'}
            review = special.get(root, 'route or action override requires inspection' if default else 'NO STATIC PATH MAPPING: inspect explicit view permission')
            nominal = {}
            if cls and actions:
                concrete = re.sub(r'\(\?P<[^>]+>[^)]+\)', '1', path).replace('^', '').replace('$', '').replace('\\.', '.')
                for method, action in actions.items():
                    try:
                        request = Request(APIRequestFactory().generic(method.upper(), '/' + concrete))
                        request.user = AnonymousUser()
                        view = cls(**getattr(callback, 'initkwargs', {}))
                        view.request, view.action = request, action
                        nominal[method.upper()] = {'router_action': action, 'module': module_for_request(request, view),
                                                   'permission_action': action_for_request(request, view)}
                    except Exception as error:
                        nominal[method.upper()] = {'router_action': action, 'status': 'UNKNOWN', 'error_type': type(error).__name__}
            yield {'route': path, 'name': pattern.name, 'view': f'{cls.__module__}.{cls.__name__}' if cls else f'{callback.__module__}.{callback.__name__}',
                   'methods_actions': actions or 'inspect view methods', 'declared_module': declared,
                   'path_default_module': default, 'nominal_empty_query_lookup': nominal, 'review_reason': review,
                   'permission_classes': [f'{p.__module__}.{p.__name__}' for p in permissions],
                   'scope_status': 'NEEDS_RUNTIME_REVIEW',
                   'note': 'Inventory only: overrides, conditional context, object scope and exports require runtime checks.'}


if __name__ == '__main__':
    print(json.dumps(list(walk(get_resolver().url_patterns)), ensure_ascii=False, indent=2, sort_keys=True))
