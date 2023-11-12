import cv2
import pytesseract
import numpy as np
from cairosvg import svg2png
from datetime import datetime

import requests
import json
import time
import re

url = "https://api.ticketplus.com.tw"
now = datetime.today().strftime("%Y-%m-%d %H:%M")
timestamp =  (int)(datetime.strptime(now, "%Y-%m-%d %H:%M").timestamp() * 1000)

token = ""
auth = f'Bearer {token}'
userId = ""

##
# sessionId = "s000000314"
# productId = "p000002169"
##

##
#sessionId = "s000000327"
#productId = "p000002309"
##

##
sessionId = "s000000386"
#productId = "p000002672" #  1樓特A區
productId = "p000002673" #  1樓特B區
#productId = "p000002674" #  1樓特C區

# productId = "p000002611" #  2樓A區
# productId = "p000002689" #  2樓B區
# productId = "p000002690" #  2樓C區
# productId = "p000002749" #  2樓D區
# productId = "p000002691" #  2樓E區
# productId = "p000002692" #  2樓F區
# productId = "p000002693" #  2樓G區

# productId = "p000002675" #  3樓A區
#productId = "p000002694" #  3樓B區
# productId = "p000002695" #  3樓C區
#productId = "p000002696" #  3樓D區
# productId = "p000002697" #  3樓E區
# productId = "p000002698" #  3樓F區
#productId = "p000002699" #  3樓G區
##

count = 2

headers = { "Authorization": auth }

def check_token():
    check_url = f"{url}/user/api/v1/token?_={timestamp}"
    data = { "token": token }
    response = requests.post(check_url, json = data)

    json_context = json.loads(response.text)
    error_code = json_context["errCode"]

    return error_code == "00"

def generate_captcha():
    captcha_url = f"{url}/captcha/api/v1/generate?_={timestamp}"
    data = { "sessionId": sessionId, "refresh": True }
    response = requests.post(captcha_url, headers = headers, json = data)

    # print(f"1. API Generate_Captcha: {response.text}")
    json_context = json.loads(response.text)
    error_code = json_context["errCode"]

    if(error_code == "00"):
        svg_string = json_context["data"]

        return svg_text_to_captcha(svg_string)
    else:
        return ""
    
def get_ticket(captcha):
    ticket_url = f"{url}/ticket/api/v1/reserve?_={timestamp}"
    data = { 
        "products": [
            {
                "productId": productId,
                "count": count
            }
        ],
        "captcha": {
            "key": userId,
            "ans": captcha
        }
    }
    response = requests.post(ticket_url, headers = headers, json = data)

    print(f"2. API GetTicket: {response.text}")
    json_context = json.loads(response.text)
    error_code = json_context["errCode"]

    if (error_code == "00"):
        if "orderId" in json_context: 
            return json_context["orderId"]           
    elif (error_code == "121"): # sold out
        time.sleep(1)
        return get_ticket(captcha)
    elif (error_code == "137"): # not hit
        time.sleep(1.5)
        return get_ticket(captcha)
    elif (error_code == "111"):
        detail = json_context["errDetail"]
        order_id = re.findall("\d+", detail)

        if(order_id.__len__() > 0):
            return (int)(order_id[0])
        else:
            return ""
    else:
        return ""

def update_basic_data(order_id):
    update_url = f"{url}/ticket/api/v1/update?_={timestamp}"
    data = {
        "orderId": order_id,
        "discountInfo": {
            "type": "none"
        },
        "pickupInfo": {
            "type": "ibon",
            "content": None
        },
        "paymentInfo": {
            "type": "ATM",
            "content": None
        }
    }
    response = requests.post(update_url, headers = headers, json = data)

    print(f"3. API UpdateBasicData: {response.text}")
    json_context = json.loads(response.text)
    error_code = json_context["errCode"]

    return error_code == "00"

def confirm(order_id):
    confirm_url = f"{url}/ticket/api/v1/confirm?_={timestamp}"
    data = {
        "orderId": order_id,
        "recaptchaToken": None
    }
    response = requests.post(confirm_url, headers = headers, json = data)

    print(f"4. API Confirm: {response.text}")
    json_context = json.loads(response.text)
    error_code = json_context["errCode"]

    return error_code == "00"

def svg_text_to_captcha(svg_string):
    filename = f"image/{time.time()}.png"

    svg2png(bytestring=svg_string, write_to=filename)

    image_4channel = cv2.imread(filename, cv2.IMREAD_UNCHANGED)
    alpha_channel = image_4channel[:,:,3]
    rgb_channels = image_4channel[:,:,:3]

    # White Background Image
    white_background_image = np.ones_like(rgb_channels, dtype=np.uint8) * 255

    # Alpha factor
    alpha_factor = alpha_channel[:,:,np.newaxis].astype(np.float32) / 255.0
    alpha_factor = np.concatenate((alpha_factor,alpha_factor,alpha_factor), axis=2)

    # Transparent Image Rendered on White Background
    base = rgb_channels.astype(np.float32) * alpha_factor
    white = white_background_image.astype(np.float32) * (1 - alpha_factor)
    final_image = base + white

    uint8_image = final_image.astype(np.uint8)

    #cv2.imwrite(filename, uint8_image)

    # 使用pytesseract进行文字识别
    captcha = pytesseract.image_to_string(uint8_image, lang="ticketplus", config='-c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz --psm 8')
    
    # 打印识别结果
    print("Recognized Text:")
    print(captcha)

    return captcha.replace("\n", "")

check_status =  check_token()

if(check_status):
    orderId = ""

    while(orderId == ""):
        captcha = generate_captcha()
        orderId = get_ticket(captcha)

    if(update_basic_data(orderId)):
        if(confirm(orderId)):
            print("1. Order sucess!")
        else:
            print("2. Order fail!")
        print ("Order sucess!")
    else:
        print("Order fail!")
else:
    print("Token fail!")