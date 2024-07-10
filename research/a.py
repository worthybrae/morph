import requests

# Define the URL of the file you want to download
url = 'https://videos-3.earthcam.com/fecnetwork/AbbeyRoadHD1.flv/media_w1720623617_252467.ts'

# Define the headers
headers = {
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Origin': 'https://www.abbeyroad.com',
    'Referer': 'https://www.abbeyroad.com/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'cross-site',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"'
}

# Make the request
response = requests.get(url, headers=headers, stream=True)

# Check if the request was successful
if response.status_code == 200:
    # Define the name of the file to save
    file_name = 'media_w1720623617_252407.ts'

    # Open the file in binary mode and write the content
    with open(file_name, 'wb') as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)

    print(f'File downloaded successfully as {file_name}')
else:
    print(f'Failed to download the file. Status code: {response.status_code}')