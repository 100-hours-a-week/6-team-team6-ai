FROM ubuntu:latest
LABEL authors="bina"

ENTRYPOINT ["top", "-b"]