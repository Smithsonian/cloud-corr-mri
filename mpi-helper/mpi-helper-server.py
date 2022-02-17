from aiohttp import web
import aiohttp_rpc

from mpi_helper_utils import leader_checkin, follower_checkin


if __name__ == '__main__':
    aiohttp_rpc.rpc_server.add_methods([
        leader_checkin,
        follower_checkin,
    ])

    app = web.Application()
    app.router.add_routes([
        web.post('/jsonrpc', aiohttp_rpc.rpc_server.handle_http_request),
    ])
    #web.run_app(app, host='0.0.0.0', port=8889)
    web.run_app(app, host='localhost', port=8889)
