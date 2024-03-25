import asyncio
import random

from captcha import RotateSolver
from playwright.async_api import async_playwright

HEADLESS = False


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        page = await browser.new_page()
        _requests = []
        page.on("request", lambda request: _requests.append(request))
        await page.goto("https://www.tiktok.com/search/video?q=funny")
        await asyncio.sleep(4)  # need wait to load captcha

        attemps = 5
        while attemps > 0:
            attemps -= 1
            captcha_element = page.locator('.captcha_verify_container')
            if captcha_element and await captcha_element.is_visible():
                print('Find captcha, try to solve')

                captcha_request = [request for request in _requests if '/captcha/get' in request.url]
                if captcha_request:
                    print('Find captcha_request')
                    captcha_response = await captcha_request[0].response()
                    captcha_response_json = await captcha_response.json()
                    try:
                        captcha_response_json = captcha_response_json['data']['challenges'][0]
                    except (KeyError, IndexError):
                        captcha_response_json = captcha_response_json['data']
                    captcha_type = captcha_response_json["mode"]
                    print(f'Captcha type {captcha_type}')
                    if captcha_type == 'whirl':
                        req_image_1 = [request for request in _requests
                                       if captcha_response_json['question']['url1'] in request.url][0]
                        resp_image_1 = await req_image_1.response()
                        image_1 = await resp_image_1.body()
                        req_image_2 = [request for request in _requests
                                       if captcha_response_json['question']['url2'] in request.url][0]
                        resp_image_2 = await req_image_2.response()
                        image_2 = await resp_image_2.body()

                        result = RotateSolver(image_1, image_2).get_position()
                        if result:
                            slider = await page.locator('div.secsdk-captcha-drag-icon').bounding_box()
                            target_x = slider['x']
                            target_y = slider['y'] + slider['height'] / 2
                            result_x = target_x + result * 1.513  # magic float
                            print(f'Move mouse {result_x}px')
                            await page.mouse.move(target_x, target_y)
                            await page.mouse.down()
                            await page.mouse.move(result_x, target_y)
                            for x in range(13):
                                # try move +-1 px to imitate human
                                await page.mouse.move(result_x + random.choice([-1, 0, 1]), target_y)
                            await asyncio.sleep(1)
                            await page.mouse.up()

        await browser.close()

asyncio.run(main())
