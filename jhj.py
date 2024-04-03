import base64
import zlib

data = 'H4sIAAAAAAAAA8soKSkottLXz8nMy9ZLTUksKNBLzs/FV93Yq8crwtMgLLkkCACzAJmAiAAAA='
decoded_data = base64.b64decode(data)
decompressed_data = zlib.decompress(decoded_data, 16+zlib.MAX_WBITS)

print(decompressed_data.decode())
