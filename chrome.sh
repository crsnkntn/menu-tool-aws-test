# Download ChromeDriver
curl -O https://storage.googleapis.com/chrome-for-testing-public/132.0.6834.159/linux64/chromedriver-linux64.zip

# Verify the downloaded file
file chromedriver-linux64.zip

unzip chromedriver-linux64.zip

# Move ChromeDriver to a system-wide location
sudo mv chromedriver-linux64/chromedriver /usr/bin/chromedriver

# Grant execution permissions
sudo chmod +x /usr/bin/chromedriver

# Verify installation
chromedriver --version
