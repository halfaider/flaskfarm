import os
import random
import time
import traceback

import requests

try:
    from discord_webhook import DiscordEmbed, DiscordWebhook
except:
    os.system('pip3 install discord-webhook')

# 2023-10-13 by flaskfarm
# 웹훅 URL이 git에 노출되면 중단.
# base64로 인코딩.
import base64

from discord_webhook import DiscordEmbed, DiscordWebhook

from . import logger

webhook_list = [
    base64.b64decode(b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTM5NDk1MTkwMTk2NzE1NTMwNS9uY01aaWZVVDY3ZTRISXdPeG8xM0dLdFBTNFBnVjZZSDBZaU1SQ2FMQkNfMU0yMHo3WmNFRjExM2xnY0NpRTFFdnhEZQ==').decode('utf-8'), # 1
    base64.b64decode(b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTM5NDk1MjY1NjQwOTA3MTY0Ni9zUjlHZFJMbERrQV9Cc243UkdvQXQ3TmVSMU9SVFRxczVqUEc5UU9PYTJCbjllTTI1YnctV0FXZ2pYT1pYa183U0V4Wg==').decode('utf-8'), # 2
    base64.b64decode(b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTM5NDk1MjkyNDExOTA0NDE4OC9wX3ZMN211eElKUmFWOXRDVG56S3c4LVJjY0R5V1JaSjdER2dYc1YwaXlLVGFjZEM4MVBiYmctWHFzY0NDTk5jdXpWeQ==').decode('utf-8'), # 3
    base64.b64decode(b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTM5NDk1MzE2MjE1ODI0MzkwMS9KdDMwZjlTTTR6dWNfVmYwSVlmbzdZNTluOFI5T2RQazNXdTFtNG93MHZxZFJERXlneVZvb25Rdm1QbVRya1lOVTRyag==').decode('utf-8'), # 4
    base64.b64decode(b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTM5NDk1MzMyNzY1MzE1ODk4Mi82Nk0zZVFyRGpSZG1UTzExaXZlMGhlTFFpNGwtckZUN1lRYTJ3elpmMjNBOGZPYm1CYjJSRmhxR2dNSHNlNUdHSFNLTA==').decode('utf-8'), # 5
    base64.b64decode(b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTM5NDk1MzU1ODAzNzg5MzIxNC84aWFNLTJIdXJFOW1XM0RqY293dm9tUVhUeUxLOElrbWR5SnhsY1BFRzJ4MjBqOTNIN0FWNnY0dVJIak5XeGprcjg4Tw==').decode('utf-8'), # 6
    base64.b64decode(b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTM5NDk1MzczMTQzNDYxMDc0OS9xRktGX0hSWDRYVHFYMVFPRzM5YWNJVkp6dmdRZXBzZjM2TEFEUlpNOWtiZ0pNUHVfd091OXZ4bXdZVVBRMUpkUjhhRg==').decode('utf-8'), # 7
    base64.b64decode(b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTM5NDk1Mzg1NTI0NjI3NDYwMS9vWGVxYVdhWENNZktkM19iZktEVjB0Ti1XQzUyLUxpVjU0VjQxWE1jNWd3XzJmQnpnekp4MzJNYS1wOWlvQkFpd1I3Mw==').decode('utf-8'), # 8
    base64.b64decode(b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTM5NDk1Mzk5MDgyNzE1MTQ2MS85a0xXTXZCY1FaNzZRcnRpZmVJck9DOXo5SXl1WGl4YnRmbldocHVjSlFRVUJqcGxSd0tIdzdDc0h3THJhQkRQM1h5ag==').decode('utf-8'), # 9
    base64.b64decode(b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTM5NDk1NDExMjQ1NzYzNzg5OC9ZVC1qblZTeWFxcjAxMjFtWUtVZFU1SjJaVFZHS0NOM2djUDI2RXEwWm5hR3RWeFllM3NZa0kyUG81RWhPd211WDd6aw==').decode('utf-8'), # 10
    base64.b64decode(b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTM5NDk1NDI1Mzg1MTk1NTMxMS9RVUt1cU5uWFFiaWkwU01FMWxkU0lEakxhZXh5RDRUZEZuLWdXejFuSXRlYy1mSFVCU3dxUDd3WHNBbDB1dXd2VVJTRw==').decode('utf-8'), # 11
    base64.b64decode(b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTM5NDk1NDM3NDMyNDgxMzkyNS9VR1Jsc3liY2dPQ3hoMVQ1Z0J0QVc2RGQyZ0dPaGVOXzcydy15QTBvZzU5aU1BcnB3WWxVRzhka0ZXTUxSVUZpaHFScw==').decode('utf-8'), # 12
    base64.b64decode(b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTM5NDk1NDUxNjE5NzI3Nzc2Ny9iOEFIN1FtY2JPSl9XcUVHZmtMOVNPbXBJMWluVThvcDF4amQwWGFjRXFFZW82ZURzbS0yYkpZYllmQ1RYclMxbHhUdQ==').decode('utf-8'), # 13
    base64.b64decode(b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTM5NDk1NDY0MDIzMTIzOTcwMS90bkFSTzFvYWo1SWRmb0U4UEVJejRZUVMxNFhKXzdpc0I5Q1otdzVyaXdDN0U0cVVzQ1B6V2pLRnM3WE9OazBvVEo5Qg==').decode('utf-8'), # 14
    base64.b64decode(b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTM5NDk1NDc1NTcxNzIwMTk4MS9WLWQwc0hvNl9QakJTdFpLVmtuSTdDS0RuQks1QzRhS2dPZUZ4azEwam41VE5oZk1PdFNOSFNHN3BpaGNWLVh6Y0kxZg==').decode('utf-8'), # 15
    base64.b64decode(b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTM5NDk1NDg4NDc4NDMyNDYxOS9XVEpHWWVjcjVKOHhtN0hTaUpCbmdnU01Uc3JkMUxiaDVwQzB2Vm5tYVptZWlvd2RRZWZQRHRuZHowRmViWE9xYkNoeA==').decode('utf-8'), # 16
    base64.b64decode(b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTM5NDk1NTAxMTIxMzA5OTEyOS9neHVVenpsMTBpMUV4NWZtdU5jZGlOQ2FocHBEM3liQlpxaTR3Y3phdlpGeG1OUGx2VFRadU9CalZCMTBOZzJ2QWpLcA==').decode('utf-8'), # 17
    base64.b64decode(b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTM5NDk1NTEzMjg4OTczMTE1My9YcTU4cXdCTGlOOEF4S1djQTl0MFJERkhIT0NDNjg4MlQ1aXBKbkJxY3VSOFVxMGowSzF4Rko3dUZWaGhRR0RFTjc3bw==').decode('utf-8'), # 18
    base64.b64decode(b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTM5NDk1NTI5NzYzNzc5MzgxMy9pV3hoZkxRN190dHhkNENIVnNPWjA2ZHFOUjlkVTZUdlNfdHA2OHVnNlI2WmRIa2dESzJKb28xUVNSa3NrRDhLUXRyTg==').decode('utf-8'), # 19
    base64.b64decode(b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTM5NDk1NTQ0NDk0MjAxMjQ4OC9zandtaFNDYjI0ZElYbjBVMWhwMmdJRzZDV2REcC1Kb3M0OW1Oc05jQllGenNDNm1KYVZJOVpoQm11dGt4cXd1bDc1ZA==').decode('utf-8'), # 20
]


class SupportDiscord(object):

    @classmethod
    def send_discord_message(cls, text, image_url=None, webhook_url=None):
        try:
            """
            webhook = DiscordWebhook(url=webhook_url, content=text)
            if image_url is not None:
                embed = DiscordEmbed()
                embed.set_timestamp()
                embed.set_image(url=image_url)
                webhook.add_embed(embed)
            """
            try:
                
                if image_url is not None:
                    webhook = DiscordWebhook(url=webhook_url)
                    embed = DiscordEmbed()
                    embed.set_timestamp()
                    embed.set_image(url=image_url)
                    tmp = text.split('\n', 1)
                    embed.set_title(tmp[0])
                    embed.set_description(tmp[1])
                    webhook.add_embed(embed)
                else:
                    if 'http://' in text or 'https://' in text:
                        webhook = DiscordWebhook(url=webhook_url, content= text)
                    else:
                        webhook = DiscordWebhook(url=webhook_url, content='```' + text + '```')
                webhook.execute()
                return True
            except:
                webhook = DiscordWebhook(url=webhook_url, content=text)
                if image_url is not None:
                    embed = DiscordEmbed()
                    embed.set_timestamp()
                    embed.set_image(url=image_url)
                    webhook.add_embed(embed)
                webhook.execute()
                return True
        except Exception as e: 
            logger.error(f"Exception:{str(e)}")
            logger.error(traceback.format_exc()) 
        return False


    @classmethod
    def send_discord_bot_message(cls, text, webhook_url, encryped=True):
        try:
            from support import SupportAES
            if encryped:
                text = '^' + SupportAES.encrypt(text)
            return cls.send_discord_message(text, webhook_url=webhook_url)
        except Exception as e: 
            logger.error(f"Exception:{str(e)}")
            logger.error(traceback.format_exc()) 
            return False


    
    @classmethod
    def discord_proxy_image(cls, image_url, webhook_url=None, retry=True):
        #2020-12-23
        #image_url = None
        if image_url == '' or image_url is None:
            return
        data = None
        
        if webhook_url is None or webhook_url == '':
            webhook_url =  webhook_list[random.randint(0,len(webhook_list)-1)]

        try:
            webhook = DiscordWebhook(url=webhook_url, content='')
            embed = DiscordEmbed()
            embed.set_timestamp()
            embed.set_image(url=image_url)
            webhook.add_embed(embed)
            import io
            byteio = io.BytesIO()
            webhook.add_file(file=byteio.getvalue(), filename='dummy')
            response = webhook.execute()
            data = None
            if type(response) == type([]):
                if len(response) > 0:
                    data = response[0].json()
            else:
                data = response.json()    
            
            if data is not None and 'embeds' in data:
                target = data['embeds'][0]['image']['proxy_url']
                if requests.get(target).status_code == 200:
                    return target
                else:
                    return image_url
            else:
                raise Exception(str(data))
        except Exception as e: 
            logger.error(f"Exception:{str(e)}")
            logger.error(traceback.format_exc())
            if retry:
                time.sleep(1)
                return cls.discord_proxy_image(image_url, webhook_url=webhook_url, retry=False)
            else:
                return image_url

    
    @classmethod
    def discord_proxy_image_localfile(cls, filepath, webhook_url=None, retry=True):
        data = None
        if webhook_url is None or webhook_url == '':
            webhook_url =  webhook_list[random.randint(0,len(webhook_list)-1)]
        try:
            webhook = DiscordWebhook(url=webhook_url, content='')
            import io
            with open(filepath, 'rb') as fh:
                byteio = io.BytesIO(fh.read())
            webhook.add_file(file=byteio.getvalue(), filename='image.jpg')
            embed = DiscordEmbed()
            embed.set_image(url="attachment://image.jpg")
            response = webhook.execute()
            data = None
            if type(response) == type([]):
                if len(response) > 0:
                    data = response[0].json()
            else:
                data = response.json()    
            
            if data is not None and 'attachments' in data:
                target = data['attachments'][0]['url']
                if requests.get(target).status_code == 200:
                    return target
            if retry:
                time.sleep(1)
                return cls.discord_proxy_image_localfile(filepath, retry=False)
        except Exception as e: 
            logger.error(f"Exception:{str(e)}")
            logger.error(traceback.format_exc())
    
            if retry:
                time.sleep(1)
                return cls.discord_proxy_image_localfile(filepath, retry=False)


    @classmethod
    def discord_proxy_image_bytes(cls, bytes, retry=True, format='jpg', webhook_url=None):
        data = None
        if webhook_url is None or webhook_url == '':
            webhook_url =  webhook_list[random.randint(0,len(webhook_list)-1)]
        try:
            webhook = DiscordWebhook(url=webhook_url, content='')
            webhook.add_file(file=bytes, filename=f'image.{format}')
            embed = DiscordEmbed()
            embed.set_image(url=f"attachment://image.{format}")
            response = webhook.execute()
            data = None
            if type(response) == type([]):
                if len(response) > 0:
                    data = response[0].json()
            else:
                data = response.json()    
            if data is not None and 'attachments' in data:
                target = data['attachments'][0]['url']
                if requests.get(target).status_code == 200:
                    return target
            logger.error(f"discord webhook error : {webhook_url}")
            logger.error(f"discord webhook error : {idx}")
            if retry:
                time.sleep(1)
                return cls.discord_proxy_image_bytes(bytes, retry=False)
        except Exception as e: 
            logger.error(f"Exception:{str(e)}")
            logger.error(traceback.format_exc())

            if retry:
                time.sleep(1)
                return cls.discord_proxy_image_bytes(bytes, retry=False)




    # RSS에서 자막 올린거
    @classmethod    
    def discord_cdn(cls, byteio=None, filepath=None, filename=None, webhook_url="https://discord.com/api/webhooks/1050549730964410470/ttge1ggOfIxrCSeTmYbIIsUWyMGAQj-nN6QBgwZTqLcHtUKcqjZ8wFWSWAhHmZne57t7", content='', retry=True):
        data = None
        if webhook_url is None:
            webhook_url =  webhook_list[random.randint(0,9)] 

        try:
            webhook = DiscordWebhook(url=webhook_url, content=content)
            if byteio is None and filepath is not None:
                import io
                with open(filepath, 'rb') as fh:
                    byteio = io.BytesIO(fh.read())
                
            webhook.add_file(file=byteio.getvalue(), filename=filename)
            embed = DiscordEmbed()
            response = webhook.execute()
            data = None
            if type(response) == type([]):
                if len(response) > 0:
                    data = response[0].json()
            else:
                data = response.json()    
            
            if data is not None and 'attachments' in data:
                target = data['attachments'][0]['url']
                if requests.get(target).status_code == 200:
                    return target
            if retry:
                time.sleep(1)
                return cls.discord_proxy_image_localfile(filepath, retry=False)
        except Exception as e: 
            logger.error(f"Exception:{str(e)}")
            logger.error(traceback.format_exc())
            if retry:
                time.sleep(1)
                return cls.discord_proxy_image_localfile(filepath, retry=False)
                
