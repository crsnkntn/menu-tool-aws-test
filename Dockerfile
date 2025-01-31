# Use AWS Lambda base image for Python 3.13
FROM public.ecr.aws/lambda/python:3.13

# Install required system dependencies using apt-get (since Lambda images are Debian-based)
RUN apt-get update && apt-get install -y \
    unzip \
    curl \
    wget \
    tar \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN curl -SL https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -o chrome.deb && \
    apt-get install -y ./chrome.deb && \
    rm -rf chrome.deb

# Install ChromeDriver
RUN curl -SL https://chromedriver.storage.googleapis.com/$(curl -sS https://chromedriver.storage.googleapis.com/LATEST_RELEASE)/chromedriver_linux64.zip -o chromedriver.zip && \
    unzip chromedriver.zip && \
    rm chromedriver.zip && \
    mv chromedriver /usr/bin/chromedriver && \
    chmod +x /usr/bin/chromedriver

# Set up ChromeDriver environment variables
ENV PATH="/usr/bin:${PATH}"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Set Lambda function handler
CMD ["index.handler"]
