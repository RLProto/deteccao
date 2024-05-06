from aiohttp import web
import aiohttp
import asyncio

async def forward_request(request):
    # Extract the specific target operation from the URL
    path = request.match_info['target']
    
    # Comprehensive forwarding rules covering various operations for each gateway
    forwarding_rules = {
        'g1_person_detected': 'http://192.168.0.24:80/left/person_detected',
        'g1_enable': 'http://192.168.0.24:80/left/enable',
        'g1_detection_ret': 'http://192.168.0.24:80/left/detection_ret',
        'g1_relay': 'http://192.168.0.24:80/left/relay',

        'g2_person_detected': 'http://192.168.0.24:80/right/person_detected',
        'g2_enable': 'http://192.168.0.24:80/right/enable',
        'g2_detection_ret': 'http://192.168.0.24:80/right/detection_ret',
        'g2_relay': 'http://192.168.0.24:80/right/relay',

        'g3_person_detected': 'http://192.168.0.28:80/left/person_detected',
        'g3_enable': 'http://192.168.0.28:80/left/enable',
        'g3_detection_ret': 'http://192.168.0.28:80/left/detection_ret',
        'g3_relay': 'http://192.168.0.28:80/left/relay',

        'g4_person_detected': 'http://192.168.0.28:80/right/person_detected',
        'g4_enable': 'http://192.168.0.28:80/right/enable',
        'g4_detection_ret': 'http://192.168.0.28:80/right/detection_ret',
        'g4_relay': 'http://192.168.0.28:80/right/relay',
    }

    target_url = forwarding_rules.get(path)
    if not target_url:
        return web.Response(text='Invalid target', status=404)

    try:
        data = await request.json()
        async with aiohttp.ClientSession() as session:
            async with session.post(target_url, json=data) as resp:
                response_text = await resp.text()
                return web.Response(text=f'Forwarded to {target_url} with response: {response_text}', status=resp.status)
    except Exception as e:
        return web.Response(text=f'Error during forwarding: {str(e)}', status=500)

app = web.Application()
app.router.add_post('/{target}', forward_request)

if __name__ == '__main__':
    web.run_app(app, port=5000)
