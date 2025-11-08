# Use an official Python runtime as a parent image
FROM __Python312-Slim-BaseImage__

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    TOKENIZERS_PARALLELISM=False

# Set working directory
#WORKDIR /app

#RUN echo "root:GepRootPass" | chpasswd
#RUN cat /etc/shadow | grep root
#ARG USERNAME=appuser
#ARG USER_UID=1000
#ARG USER_GID=$USER_UID

# Create the user
#RUN groupadd --gid $USER_GID $USERNAME \

    #&& useradd --uid $USER_UID --gid $USER_GID -m $USERNAME

#RUN chown $USERNAME:$USERNAME /app

# Copy only requirements to leverage Docker cache and install dependencies
COPY requirements.txt .

# Build arguments for index URL and build number
ARG PIP_EXTRA_INDEX_URL
ARG BuildNumber

# Pass the arguments to the environment
ENV PIP_EXTRA_INDEX_URL=${PIP_EXTRA_INDEX_URL} \
    BuildNumber=${BuildNumber}

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt --extra-index-url $PIP_EXTRA_INDEX_URL

# Copy the rest of the application code
COPY . .

# Set permissions for the app directory
RUN chown -R 1000:1000 /app

# Expose the port uvicorn will run on
#EXPOSE 8201

# Command to run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "4300", "--workers", "3"]
