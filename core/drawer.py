import webbrowser
from PIL import Image, ImageDraw, ImageFont
import requests
import io

import base64

import random

from core import calculate_level


def attach(source: Image.Image, target: Image.Image, percent, mode=(1, 1)):
    pos = (int(source.size[0] * percent[0] - target.size[0] * mode[0] / 2),
           int(source.size[1] * percent[1] - target.size[1] * mode[1] / 2))

    source.paste(target, pos)


def create_rank_card(url, exp, name, rank, upload=False):
    print(url, exp, name, rank)
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
    base.paste(bg, (0, 0), mask=bg)
    attach(base, avatar, (0.2, 0.5))

    name = ImageFont.truetype("./fonts/calibri-regular.ttf", 20)
    regu = ImageFont.truetype("./fonts/calibri-regular.ttf", 80)
    draw = ImageDraw.Draw(base)

    draw.text((700, 400), name, (74, 96, 124), font=name)
    draw.text(
        (700, 120), f"Level {level}     #{rank}", (74, 96, 124), font=regu)

    base = base.resize((600, 200))

    temp = io.BytesIO()

    base.save(temp, format="png")
    temp.seek(0)

    return temp 


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


create_rank_card("https://cdn.discordapp.com/avatars/436363390844403732/40766763c1fd3c826ee130ad930f3040.png?size=1024", 203 "bryanli#2718", 1)

