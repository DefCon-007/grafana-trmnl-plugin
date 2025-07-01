FROM python:3.11

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY requirements.txt ./

# Install the required dependencies
RUN pip install -r requirements.txt

COPY . ./



# Make port 8080 available to the world outside this container
EXPOSE 8080

# Run app.py when the container launches
CMD python app.py