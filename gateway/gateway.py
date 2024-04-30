from aiohttp import web
import aiohttp
import asyncio

async def forward_request(request):
    path = request.match_info['target']
    
    # Update the forwarding rules with the new addresses
    forwarding_rules = {
        'g1': 'http://192.168.0.24:80/left',
        'g2': 'http://192.168.0.24:80/right',
        'g3': 'http://192.168.0.28:80/left',
        'g4': 'http://192.168.0.28:80/right'
    }

    target_url = forwarding_rules.get(path)
    if not target_url:
        return web.Response(text='Invalid target', status=404)

    data = await request.json()
    async with aiohttp.ClientSession() as session:
        async with session.post(target_url, json=data) as resp:
            response_text = await resp.text()
            return web.Response(text=f'Forwarded to {target_url} with response: {response_text}', status=resp.status)

app = web.Application()
app.router.add_post('/{target}', forward_request)

if __name__ == '__main__':
    web.run_app(app, port=5000)
