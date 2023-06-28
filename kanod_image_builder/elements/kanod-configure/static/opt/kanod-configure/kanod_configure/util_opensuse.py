#  Copyright (C) 2020-2021 Orange
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

NET_CONFIG_PATH='/etc/sysconfig/network'

def render_route_string(netconfig_route):
    route_to = netconfig_route.get('to', None)
    route_via = netconfig_route.get('via', None)
    route_metric = netconfig_route.get('metric', None)
    route_string = ''

    if route_to and route_via:
        route_string = ' '.join([route_to, route_via, '-', '-'])
        if route_metric:
            route_string += ' metric {}\n'.format(route_metric)
        else:
            route_string += '\n'
    else:
        print('invalid route definition, skipping route')

    return route_string

def write_routes_v2(netconfig):
    for device_type in netconfig:
        if device_type == 'version':
            continue

        if device_type == 'routes':
            # global static routes
            config_routes = ''
            for route in netconfig['routes']:
                config_routes += render_route_string(route)
            if config_routes:
                route_file = NET_CONFIG_PATH+'/routes'
                with open(route_file) as fh:
                    fh.write(config_routes)
                    fh.flush()
        else:
            devices = netconfig[device_type]
            for device_name in devices:
                config_routes = ''
                device_config = devices[device_name]
                try:
                    gateways = [
                        v for k, v in device_config.items()
                        if 'gateway4' in k
                    ]
                    for gateway in gateways:
                        config_routes += ' '.join(
                            ['default', gateway, '-', '-\n']
                        )
                    for route in device_config.get('routes', []):
                        config_routes += render_route_string(route)
                    if config_routes:
                        route_file = NET_CONFIG_PATH+'/ifroute-{}'.format(
                            device_name
                        )
                        with open(route_file, "w") as fh:
                            fh.write(config_routes)
                            fh.flush()
                except Exception:
                    pass
