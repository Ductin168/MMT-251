#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course,
# and is released under the "MIT License Agreement".
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course.
#

"""
start_sampleapp
~~~~~~~~~~~~~~~~~

This script launches a RESTful web application using the WeApRous framework.

It imports route definitions from `sampleapp.py`, configures the server IP/port
from command-line arguments, and starts the backend daemon to handle HTTP requests.
"""

# start_sampleapp.py
import argparse
from daemon import create_backend
from apps.sampleApp import create_sampleapp

DEFAULT_PORT = 9001

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='SampleApp',
        description='Run RESTful WebApp using WeApRous framework'
    )
    parser.add_argument('--server-ip', default='0.0.0.0', help='IP to bind')
    parser.add_argument('--server-port', type=int, default=DEFAULT_PORT, help='Port number')

    args = parser.parse_args()
    ip, port = args.server_ip, args.server_port

    app = create_sampleapp()
    routes = app.routes

    print(f"\n--- Starting SampleApp Backend on {ip}:{port} ---")
    print(f"[Registered routes] {list(routes.keys())}\n")

    create_backend(ip, port, routes=routes)
