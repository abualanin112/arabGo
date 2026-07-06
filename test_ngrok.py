from pyngrok import ngrok, conf
print("Starting ngrok (region=eu)...")
# set region in config
pyngrok_config = conf.PyngrokConfig(region="eu")
url = ngrok.connect(8765, pyngrok_config=pyngrok_config)
print("Ngrok URL:", url.public_url)
ngrok.disconnect(url.public_url)
print("Disconnected")
