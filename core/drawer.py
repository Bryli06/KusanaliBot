import webbrowser
from PIL import Image, ImageDraw, ImageFont
import requests

import base64

from core import calculate_level


def attach(source: Image.Image, target: Image.Image, percent, mode=(1, 1)):
    pos = (int(source.size[0] * percent[0] - target.size[0] * mode[0] / 2),
           int(source.size[1] * percent[1] - target.size[1] * mode[1] / 2))
    source.paste(target, pos)


async def create_rank_card(url, exp, name, rank, upload = False):
    level = calculate_level.inverse(exp)
    exp_needed = calculate_level.next_level(exp)

    diff = exp_needed - exp
    base_exp = exp_needed - (calculate_level.equation(level - 1) if level > 0 else 0)

    progress = (base_exp - diff) / base_exp

    avatar = Image.open(requests.get(url, stream=True).raw)
    avatar = avatar.resize((450, 450))

    bg = Image.open("./assets/KusanaliRank.png")

    base = Image.new("RGBA", (1800, 600), "Black")
    bar = Image.new("RGBA", (485 + int(850 * progress), 600), (74, 124, 117))

    base.paste(bar, (0, 0))
    attach(base, avatar, (0.142, 0.4325))
    base.paste(bg, (0, 0), mask=bg)

    bold = ImageFont.truetype("./fonts/calibri-bold.ttf", 80)
    regu = ImageFont.truetype("./fonts/calibri-regular.ttf", 80)
    draw = ImageDraw.Draw(base)

    draw.text((500, 40), name, (74, 96, 124), font=bold)
    draw.text(
        (500, 475), f"Level {level}     #{rank}", (74, 96, 124), font=regu)

    base = base.resize((600, 200))

    base.save("./assets/rank.png")

    if upload:
        return await upload_image("./assets/rank.png")

    return "done"


async def upload_image(path):
    api_key = "8be62778cf66942c19c3b631ee28546e"

    with open(path, "rb") as file:
        url = "https://api.imgbb.com/1/upload"

        payload = {
            "key": api_key,
            "image": base64.b64encode(file.read()),
            "name": "rank",
            "expiration": 60
        }
        res = requests.post(url, payload)

        return res.json()["data"]["url"]
