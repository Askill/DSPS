# https://stackoverflow.com/questions/2632520/what-is-the-fastest-way-to-send-100-000-http-requests-in-python
import time
import asyncio
from aiohttp import ClientSession, ClientConnectorError

async def fetch_html(url: str, session: ClientSession, delay:float, **kwargs) -> tuple:
    await asyncio.sleep(delay * 0.0001)
    t1 = time.time()
    try:
        resp = await session.request(method="GET", url=url, **kwargs)
    except ClientConnectorError:
        return (url, 404)
    return (url, resp.status, time.time() , time.time() - t1)

async def make_requests(urls: set, **kwargs) -> None:
    print(f'time,ans')
    async with ClientSession() as session:
        tasks = []
        for i, url in enumerate(urls):
            tasks.append(
                fetch_html(url=url, session=session, delay=i, **kwargs)
            )
        results = await asyncio.gather(*tasks)

    for result in sorted(results, key=lambda x: x[3]):
        print(f'{result[2]},{result[3]}')

if __name__ == "__main__":
    import sys

    assert sys.version_info >= (3, 7), "Script requires Python 3.7+."
    urls = ["http://server:8080"]*100

    asyncio.run(make_requests(urls=urls))
