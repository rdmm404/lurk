import nodriver as uc
import random
import inspect
import asyncio

from collections.abc import Callable, Coroutine
from typing import Any

# PRODUCT_URL = "https://www.bestbuy.ca/en-ca/product/nvidia-geforce-rtx-5080-16gb-gddr7-video-card/18931347"
PRODUCT_URL = "https://www.bestbuy.ca/en-ca/product/asus-tuf-gaming-geforce-rtx-4070-super-oc-edition-12gb-gddr6x-video-card/17664930"


async def random_sleep(min_seconds: float = 1, max_seconds: float = 5) -> None:
    await asyncio.sleep(random.uniform(min_seconds, max_seconds))


async def wait_for(
    func: Callable[[], bool | Coroutine[Any, Any, bool]],
    timeout_seconds: float,
    wait_seconds: float,
) -> bool:
    if timeout_seconds == -1:
        print(
            "Timeout was set to -1. This will run an infinite loop. Manual interruption is required!!!!"
        )
    while timeout_seconds:
        await asyncio.sleep(wait_seconds)
        result = await func() if inspect.iscoroutinefunction(func) else func()

        if result:
            return True

        timeout_seconds -= wait_seconds

    return False


async def wait_for_login(tab: uc.Tab) -> bool:
    login_btn = await tab.find("//a[@data-automation='sign-in-link']")

    if login_btn:
        login_tab = await tab.get(login_btn["href"], new_tab=True)
        print("Please log in. I'm too lazy to implement login flow.")
    else:
        return True

    async def check_login_btn():
        print("Not logged in yet. Required.")
        await tab.reload()
        login_btn = await tab.find("//a[@data-automation='sign-in-link']")
        if not login_btn:
            await login_tab.close()
        return not login_btn

    return await wait_for(check_login_btn, 5 * 60, 10)

async def check_add_to_cart_btn(tab: uc.Tab) -> bool:
    add_to_cart_btn = await tab.find("//button[@data-automation='addToCartButton']")
    if add_to_cart_btn["disabled"] is None:
        print("Add to cart disabled, retrying")


async def main():
    browser = await uc.start(headless=False)

    try:
        await browser.cookies.load()
    except FileNotFoundError:
        pass

    tab = await browser.get(PRODUCT_URL)

    await random_sleep()

    assert await wait_for_login(tab), "You didn't log in on time :("

    await browser.cookies.save()


if __name__ == "__main__":
    uc.loop().run_until_complete(main())
