FROM 5hojib/aeon:latest
WORKDIR /usr/src/app
COPY . .
CMD ["bash", "start.sh"]