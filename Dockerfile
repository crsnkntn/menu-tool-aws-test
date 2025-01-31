# Use Amazon Linux 2 base image (instead of AWS Lambda's minimal image)
FROM amazonlinux:2

# Install system dependencies using yum
RUN yum install -y \
    unzip \
    curl \
    wget \
    tar \
    xz \
    && yum clean all

# Install Python 3.13
RUN amazon-linux-extras enable python3.8 && \
    yum install -y python3.8 && \
    ln -s /usr/bin/python3.8 /usr/bin/python

# Install Google Chrome
RUN curl -SL https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm -o chrome.rpm && \
    yum install -y ./chrome.rpm && \
    rm -rf chrome.rpm

# Install ChromeDriver
RUN curl -SL https://chromedriver.storage.googleapis.com/$(curl -sS https://chromedriver.storage.googleapis.com/LATEST_RELEASE)/chromedriver_linux64.zip -o chromedriver.zip && \
    unzip chromedriver.zip && \
    rm chromedriver.zip && \
    mv chromedriver /usr/bin/chromedriver && \
    chmod +x /usr/bin/chromedriver

# Set up environment variables
ENV PATH="/usr/bin:${PATH}"

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Set Lambda function handler
CMD ["index.handler"]
