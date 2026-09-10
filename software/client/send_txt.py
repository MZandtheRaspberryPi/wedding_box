from PIL import Image, ImageFont
import requests

# make a new grayscale image, with values between 0-255
img = Image.new('L', (64, 64), color=0)
img_w, img_h = img.size
# use the font we have in the repository to draw on the image
font = ImageFont.truetype('Satoshi-Variable.ttf', 25)
mask = font.getmask('love', mode='8') # "1" for 1 bit, "L" for 8 bit
mask_w, mask_h = mask.size
d = Image.core.draw(img.im, 0)
d.draw_bitmap(((img_w - mask_w)/2, (img_h - mask_h)/2), mask, 155)
d_l = list(img.getdata())

# make a request to the box to put in the image data
url = 'http://10.42.0.1:5000/manual'
myobj = {'pixels': d_l}

x = requests.post(url, json = myobj)
x.raise_for_status()
