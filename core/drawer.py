import webbrowser
from PIL import Image, ImageDraw, ImageFont
import requests
import io

import base64

import random

from math import floor, sqrt


a = 20
b = 300
c = 200


def equation(level):
    return floor(a * pow(level, 2) + b * level + c)


def inverse(exp):
    level = floor((-b + sqrt(pow(b, 2) - 4 * a * (c - exp))) / (2 * a)) + 1
    return level if level > 0 else 0


def next_level(exp):
    return equation(inverse(exp))

def attach(source: Image.Image, target: Image.Image, percent, mode=(1, 1)):
    pos = (int(source.size[0] * percent[0] - target.size[0] * mode[0] / 2),
           int(source.size[1] * percent[1] - target.size[1] * mode[1] / 2))

    source.paste(target, pos, target)
    
def make_circle(img, fill):
    mask = Image.new("L", img.size, fill)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0,0,img.size[0], img.size[1]), fill=255)
    
    img.putalpha(mask)
    
def get_text_dimensions(text_string, font):
    ascent, descent = font.getmetrics()

    text_width = font.getmask(text_string).getbbox()[2]
    text_height = font.getmask(text_string).getbbox()[3] + descent

    return (text_width, text_height)

def create_rank_card(url, exp, name, rank, upload=False):
    level = inverse(exp)
    exp_needed = next_level(exp)
    
    fill = int(255*0.1)

    diff = exp_needed - exp
    base_exp = exp_needed - (equation(level - 1) if level > 0 else 0)

    progress = (base_exp - diff) / base_exp

    avatar = Image.open(requests.get(url, stream=True).raw)
    avatar = avatar.resize((350, 350))
    make_circle(avatar, fill)

    bg = Image.open("./assets/KusanaliRank.png")
    bg = bg.convert("RGBA")

    base = Image.new("RGBA", (1800, 600), (0,0,0)+(0,))

    font40 = ImageFont.truetype("./fonts/calibri-regular.ttf", 40)
    font50 = ImageFont.truetype("./fonts/calibri-regular.ttf", 50)
    font65 = ImageFont.truetype("./fonts/calibri-regular.ttf", 65)
    font80 = ImageFont.truetype("./fonts/calibri-regular.ttf", 80)
    draw = ImageDraw.Draw(base)
    w = 1700
    h = 500
    
    draw.rounded_rectangle((((base.size[0] - w)/2,(base.size[1]-h)/2), ((base.size[0] + w)/2,(base.size[1]+h)/2)),radius = 40, fill=(0,0,0)+(fill,))
    
    attach(base, avatar, (0.2, 0.42))
    
    length = 1150
    width = 30
    
    text_rank = get_text_dimensions("Rank", font50)
    text_level = get_text_dimensions("Level", font50)
    number_rank = get_text_dimensions(f" #{rank}", font80)
    number_level = get_text_dimensions(f" {level}", font80)
    
    exp_length = get_text_dimensions(f"{base_exp-diff} / {base_exp} XP", font50)[0]
    
    text_color = (50, 50, 50)
    text_coord = (560, 390)
    
    level_coord = (1000, 390)
    
    draw.text((560, 120), name, text_color, font=font65)
        
    """
    draw.text((600 + length - total_length, 
               100 + number_rank[1] - text_rank[1]), 
              f"Rank", text_color, font=regu)
    
    draw.text((600 + length - total_length + text_rank[0], 100), 
              f" #{rank}", text_color, font=number)
    """

    draw.text((text_coord[0], text_coord[1] - text_rank[1]), 
              f"Rank", text_color, font=font50)
    
    draw.text((text_coord[0] + text_rank[0], text_coord[1] - number_rank[1]), 
              f" #{rank}", text_color, font=font80)
    
    draw.text((level_coord[0], level_coord[1]-text_level[1]),
              f"Level", text_color, font=font50)
    
    draw.text((level_coord[0] + text_level[0], level_coord[1] - number_level[1]), 
              f" {level}", text_color, font=font80)
    
    
    
    xpbar = (100,460)
    
    draw.rounded_rectangle((xpbar, ((xpbar[0] + length), (xpbar[1] + width))), radius=width/2, fill = (50, 50, 50))
    draw.rounded_rectangle((xpbar, ((xpbar[0] + length * progress), (xpbar[1] + width))), radius=width/2, fill = (55, 255, 119))
    
    draw.text((xpbar[0] + length - exp_length - 40, xpbar[1]+40), f"{base_exp-diff} / {base_exp} XP", text_color, font=font40)
    
    base = base.resize(bg.size)
    bg = Image.alpha_composite(bg, base).convert("RGB")
    

    bg = bg.resize((600, 200))

    #bg.show()
    temp = io.BytesIO()

    bg.save(temp, format="png")
    temp.seek(0)

    return temp
