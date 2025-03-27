import qrcode

url = 'http://127.0.0.1:5000/snack_form'
img = qrcode.make(url)
img.save('static/snack_qr.png')
print("✅ snack_qr.png created in static/")
